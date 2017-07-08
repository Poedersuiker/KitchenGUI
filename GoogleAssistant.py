import json
import logging
import os.path
import threading

import click
import grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.embedded.v1alpha1 import embedded_assistant_pb2
from google.rpc import code_pb2
from tenacity import retry, stop_after_attempt, retry_if_exception

try:
    from GoogleExample import (
        assistant_helpers,
        audio_helpers
    )
except SystemError:
    import assistant_helpers
    import audio_helpers


ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.ConverseResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.ConverseResult.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.ConverseResult.CLOSE_MICROPHONE
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5


class KitchenAssistant(object):
    """copy/change from Sample Assistant that supports follow-on conversations.

    Args:
      conversation_stream(ConversationStream): audio stream
        for recording query and playing back assistant answer.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, conversation_stream, channel, deadline_sec, chatbox):
        self.chatbox = chatbox
        self.conversation_stream = conversation_stream

        # Opaque blob provided in ConverseResponse that,
        # when provided in a follow-up ConverseRequest,
        # gives the Assistant a context marker within the current state
        # of the multi-Converse()-RPC "conversation".
        # This value, along with MicrophoneMode, supports a more natural
        # "conversation" with the Assistant.
        self.conversation_state = None

        # Create Google Assistant API gRPC client.
        self.assistant = embedded_assistant_pb2.EmbeddedAssistantStub(channel)
        self.deadline = deadline_sec

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False
        self.conversation_stream.close()

    def is_grpc_error_unavailable(e):
        is_grpc_error = isinstance(e, grpc.RpcError)
        if is_grpc_error and (e.code() == grpc.StatusCode.UNAVAILABLE):
            logging.error('grpc unavailable error: %s', e)
            return True
        return False

    @retry(reraise=True, stop=stop_after_attempt(3),
           retry=retry_if_exception(is_grpc_error_unavailable))
    def converse(self):
        """Send a voice request to the Assistant and playback the response.

        Returns: True if conversation should continue.
        """
        continue_conversation = False

        self.conversation_stream.start_recording()
        logging.info('Recording audio request.')

        def iter_converse_requests():
            for c in self.gen_converse_requests():
                assistant_helpers.log_converse_request_without_audio(c)
                yield c
            self.conversation_stream.start_playback()

        # This generator yields ConverseResponse proto messages
        # received from the gRPC Google Assistant API.
        for resp in self.assistant.Converse(iter_converse_requests(),
                                            self.deadline):
            assistant_helpers.log_converse_response_without_audio(resp)

            if len(resp.audio_out.audio_data) == 0:
                print(resp)

            if resp.error.code != code_pb2.OK:
                logging.error('server error: %s', resp.error.message)
                break
            if resp.event_type == END_OF_UTTERANCE:
                logging.info('End of audio request detected')
                self.conversation_stream.stop_recording()
            if resp.result.spoken_request_text:
                logging.info('Transcript of user request: "%s".',
                             resp.result.spoken_request_text)
                logging.info('Playing assistant response.')
            if len(resp.audio_out.audio_data) > 0:
                self.conversation_stream.write(resp.audio_out.audio_data)
            if resp.result.spoken_response_text:
                logging.info(
                    'Transcript of TTS response '
                    '(only populated from IFTTT): "%s".',
                    resp.result.spoken_response_text)
            if resp.result.conversation_state:
                self.conversation_state = resp.result.conversation_state
            if resp.result.volume_percentage != 0:
                self.conversation_stream.volume_percentage = (
                    resp.result.volume_percentage
                )
            if resp.result.microphone_mode == DIALOG_FOLLOW_ON:
                continue_conversation = True
                logging.info('Expecting follow-on query from user.')
            elif resp.result.microphone_mode == CLOSE_MICROPHONE:
                continue_conversation = False
        logging.info('Finished playing assistant response.')
        self.conversation_stream.stop_playback()
        return continue_conversation

    def gen_converse_requests(self):
        """Yields: ConverseRequest messages to send to the API."""

        converse_state = None
        if self.conversation_state:
            logging.debug('Sending converse_state: %s',
                          self.conversation_state)
            converse_state = embedded_assistant_pb2.ConverseState(
                conversation_state=self.conversation_state,
            )
        config = embedded_assistant_pb2.ConverseConfig(
            audio_in_config=embedded_assistant_pb2.AudioInConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
            ),
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
                volume_percentage=self.conversation_stream.volume_percentage,
            ),
            converse_state=converse_state
        )
        # The first ConverseRequest must contain the ConverseConfig
        # and no audio data.
        yield embedded_assistant_pb2.ConverseRequest(config=config)
        for data in self.conversation_stream:
            # Subsequent requests need audio data, but not config.
            yield embedded_assistant_pb2.ConverseRequest(audio_in=data)


class KitchenAssistentThread(threading.Thread):

    def __init__(self, chatbox, api_endpoint=ASSISTANT_API_ENDPOINT, credentials=os.path.join(click.get_app_dir('google-oauthlib-tool'),'credentials.json'), verbose=False, audio_sample_rate=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE, audio_sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH, audio_iter_size=audio_helpers.DEFAULT_AUDIO_ITER_SIZE, audio_block_size=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE, audio_flush_size=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE, grpc_deadline=DEFAULT_GRPC_DEADLINE):
        threading.Thread.__init__(self)

        self.api_endpoint = api_endpoint
        self.credentials = credentials
        self.verbose = verbose
        self.audio_sample_rate = audio_sample_rate
        self.audio_sample_width = audio_sample_width
        self.audio_iter_size = audio_iter_size
        self.audio_block_size = audio_block_size
        self.audio_flush_size = audio_flush_size
        self.grpc_deadline = grpc_deadline

        self.chatbox = chatbox
        self.running = True

        # Setup logging.
        logging.basicConfig(level=logging.DEBUG if self.verbose else logging.INFO)

        # Load OAuth 2.0 credentials.
        try:
            with open(self.credentials, 'r') as f:
                self.credentials = google.oauth2.credentials.Credentials(token=None,
                                                                    **json.load(f))
                self.http_request = google.auth.transport.requests.Request()
                self.credentials.refresh(self.http_request)
        except Exception as e:
            logging.error('Error loading credentials: %s', e)
            logging.error('Run google-oauthlib-tool to initialize '
                          'new OAuth 2.0 credentials.')
            return

        # Create an authorized gRPC channel.
        self.grpc_channel = google.auth.transport.grpc.secure_authorized_channel(self.credentials, self.http_request, self.api_endpoint)
        logging.info('Connecting to %s', self.api_endpoint)

        # Configure audio source and sink.
        self.audio_device = None
        self.audio_source = self.audio_device = (
            self.audio_device or audio_helpers.SoundDeviceStream(
                sample_rate=self.audio_sample_rate,
                sample_width=self.audio_sample_width,
                block_size=self.audio_block_size,
                flush_size=self.audio_flush_size
            )
        )
        self.audio_sink = self.audio_device = (
            self.audio_device or audio_helpers.SoundDeviceStream(
                sample_rate=self.audio_sample_rate,
                sample_width=self.audio_sample_width,
                block_size=self.audio_block_size,
                flush_size=self.audio_flush_size
            )
        )
        # Create conversation stream with the given audio source and sink.
        self.conversation_stream = audio_helpers.ConversationStream(
            source=self.audio_source,
            sink=self.audio_sink,
            iter_size=self.audio_iter_size,
            sample_width=self.audio_sample_width,
        )

    def run(self):
        with KitchenAssistant(self.conversation_stream,
                              self.grpc_channel, self.grpc_deadline, self.chatbox) as assistant:
            while self.running:
                continue_conversation = assistant.converse()

    def stop(self):
        self.running = False

if __name__ == '__main__':
    chatbox = []
    ga = KitchenAssistentThread(chatbox)
    ga.start()


