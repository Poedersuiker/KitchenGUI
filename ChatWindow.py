import gi
gi.require_version("Gtk", "3.0")
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, Gdk, WebKit
import threading
from time import sleep


class ChatWindow(Gtk.ScrolledWindow):
    def __init__(self):
        page_size = Gtk.Adjustment(lower=10, page_size=100)
        super(ChatWindow, self).__init__(page_size)
        self.set_border_width(10)
        self.set_hexpand(True)
        self.listbox = Gtk.ListBox()
        self.add(self.listbox)

    def send_msg(self, msg):
        lbr = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lbr.add(box)
        self.listbox.add(lbr)

        name = Gtk.Label()
        name.set_markup("<big><b>Me</b></big>:")
        name.set_justify(Gtk.Justification.RIGHT)
        name.set_halign(Gtk.Align.END)
        msg_label = Gtk.Label(msg)
        msg_label.set_justify(Gtk.Justification.RIGHT)
        msg_label.set_halign(Gtk.Align.END)
        box.add(name)
        box.add(msg_label)
        box.show_all()
        lbr.show_all()

    def receive_msg(self, who, msg):
        lbr = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lbr.add(box)
        self.listbox.add(lbr)

        name = Gtk.Label()
        name.set_markup("<big><b>{0}</b></big>:".format(who))
        name.set_justify(Gtk.Justification.LEFT)
        name.set_halign(Gtk.Align.START)
        msg_label = Gtk.Label(msg)
        msg_label.set_justify(Gtk.Justification.LEFT)
        msg_label.set_halign(Gtk.Align.START)
        box.add(name)
        box.add(msg_label)
        box.show_all()
        lbr.show_all()


class chatter(threading.Thread):
    def __init__(self, chatpage):
        threading.Thread.__init__(self)
        self.running = True
        self.chatpage = chatpage

    def run(self):
        n = 0
        while self.running:
            self.chatpage.send_msg("test")
            sleep(0.5)
            self.chatpage.receive_msg("Tester", "test {0}".format(n))
            sleep(0.5)
            n += 1

if __name__ == '__main__':
    window = Gtk.Window()
    window.connect("delete-event", Gtk.main_quit)

    notebook = Gtk.Notebook()
    window.add(notebook)

    chatwindow = ChatWindow()
    notebook.append_page(chatwindow, Gtk.Label("GoogleA chat"))

    window.show_all()

    testthread = chatter(chatwindow)
    testthread.start()

    Gtk.main()

