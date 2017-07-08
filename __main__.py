import gi
gi.require_version("Gtk", "3.0")
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, Gdk, WebKit
from ChatWindow import ChatWindow
from GoogleCloud import SmartHomeCommands


class SmartHomeWindow(Gtk.Window):
    def __init__(self):
        self.webpages = []

        Gtk.Window.__init__(self, title="SmartHome Kitchen")
        # self.fullscreen()
        self.set_border_width(3)

        self.notebook = Gtk.Notebook()
        self.add(self.notebook)

        self.chat_page = ChatWindow()
        self.sh_commands = SmartHomeCommands(self.chat_page)
        self.notebook.append_page(self.chat_page, Gtk.Label("GoogleA chat"))

        self.home_page = Gtk.Box()
        self.home_page.set_border_width(10)
        self.home_page.add(Gtk.Label("Home Page"))
        self.notebook.append_page(self.home_page, Gtk.Label("Smart Home Page"))

        page_size = Gtk.Adjustment(lower=10, page_size=100)
        scrollwindow = Gtk.ScrolledWindow(page_size)
        web_page = WebKit.WebView()
        web_page.load_uri("https://www.google.com")
        scrollwindow.add(web_page)
        self.add_tab(scrollwindow, 'Google')
        self.webpages.append(web_page)

    def add_tab(self, widget, label_str):
        hbox = Gtk.HBox(False, 0)
        label = Gtk.Label(label_str)
        hbox.pack_start(label, True, True, 0)

        close_img = Gtk.Image()
        close_img.set_from_stock(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU)

        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_focus_on_click(False)
        btn.add(close_img)
        hbox.pack_start(btn, False, False, 0)

        btn.connect('clicked', self.on_closetab_button_clicked, widget)

        hbox.show_all()
        self.notebook.append_page(widget, hbox)

    def on_closetab_button_clicked(self, sender, widget):
        pagenum = self.notebook.page_num(widget)
        self.notebook.remove_page(pagenum)

    def on_newtab_button(self):
        print("Pressed new")


def keypress(window, event):
    key = Gdk.keyval_name(event.keyval)
    print(key)

    if key == "F11":
        window.is_fullscreen = not getattr(window, 'is_fullscreen', False)
        action = window.fullscreen if window.is_fullscreen else window.unfullscreen
        action()

window = SmartHomeWindow()
window.connect("delete-event", Gtk.main_quit)
window.connect("key-press-event", keypress)
window.show_all()
Gtk.main()
