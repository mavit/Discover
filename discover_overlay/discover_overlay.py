#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio
import select
from .voice_settings import VoiceSettingsWindow
from .text_settings import TextSettingsWindow
from .voice_overlay import VoiceOverlayWindow
from .text_overlay import TextOverlayWindow
from .discord_connector import DiscordConnector
from .general_settings import GeneralSettingsWindow
import logging
import pidfile
import os
import sys

try:
    from xdg.BaseDirectory import xdg_config_home
except ModuleNotFoundError:
    from xdg import XDG_CONFIG_HOME as xdg_config_home


class Discover:
    def __init__(self, rpc_file, args):
        self.create_gui()
        self.connection = DiscordConnector(
            self.text_settings, self.voice_settings,
            self.text_overlay, self.voice_overlay)
        self.connection.connect()
        GLib.timeout_add((1000 / 60), self.connection.do_read)
        self.rpc_file = rpc_file
        rpc_file = Gio.File.new_for_path(rpc_file)
        monitor = rpc_file.monitor_file(0, None)
        monitor.connect("changed", self.rpc_changed)
        self.do_args(args)

        try:
            Gtk.main()
        except:
            pass

    def do_args(self, data):
        if "--help" in data:
            pass
        elif "--about" in data:
            pass
        elif "--configure-general" in data:
            self.show_gsettings()
        elif "--configure-voice" in data:
            self.show_vsettings()
        elif "--configure-text" in data:
            self.show_tsettings()
        elif "--configure" in data:
            self.show_tsettings()
            self.show_vsettings()
            self.show_gsettings()
        elif "--close" in data:
            sys.exit(0)


    def rpc_changed(self, a=None, b=None, c=None,d=None):
        with open (self.rpc_file, "r") as tfile:
            data=tfile.readlines()
            if len(data)>=1:
                self.do_args(data[0])

    def create_gui(self):
        self.voice_overlay = VoiceOverlayWindow(self)
        self.text_overlay = TextOverlayWindow(self)
        self.menu = self.make_menu()
        self.make_sys_tray_icon(self.menu)
        self.voice_settings = VoiceSettingsWindow(self.voice_overlay)
        self.text_settings = TextSettingsWindow(self.text_overlay)
        self.general_settings = GeneralSettingsWindow(self.text_overlay, self.voice_overlay)

    def make_sys_tray_icon(self, menu):
        # Create AppIndicator
        try:
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3
            self.ind = AppIndicator3.Indicator.new(
                "discover_overlay",
                "discover-overlay",
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
            self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.ind.set_menu(menu)
        except Exception as e:
            # Create System Tray
            logging.info("Falling back to Systray : %s" % (e))
            self.tray = Gtk.StatusIcon.new_from_icon_name("discover_overlay")
            self.tray.connect('popup-menu', self.show_menu)

    def make_menu(self):
        # Create System Menu
        menu = Gtk.Menu()
        vsettings_opt = Gtk.MenuItem.new_with_label("Voice Settings")
        tsettings_opt = Gtk.MenuItem.new_with_label("Text Settings")
        gsettings_opt = Gtk.MenuItem.new_with_label("General Settings")
        close_opt = Gtk.MenuItem.new_with_label("Close")

        menu.append(vsettings_opt)
        menu.append(tsettings_opt)
        menu.append(gsettings_opt)
        menu.append(close_opt)

        vsettings_opt.connect("activate", self.show_vsettings)
        tsettings_opt.connect("activate", self.show_tsettings)
        gsettings_opt.connect("activate", self.show_gsettings)
        close_opt.connect("activate", self.close)
        menu.show_all()
        return menu

    def show_menu(self, obj, button, time):
        self.menu.show_all()
        self.menu.popup(
            None, None, Gtk.StatusIcon.position_menu, obj, button, time)

    def show_vsettings(self, obj=None, data=None):
        self.voice_settings.present()

    def show_tsettings(self, obj=None, data=None):
        self.text_settings.present()

    def show_gsettings(self, obj=None, data=None):
        self.general_settings.present()

    def close(self, a=None, b=None, c=None):
        Gtk.main_quit()


def entrypoint():
    configDir = os.path.join(xdg_config_home, "discover_overlay")
    os.makedirs(configDir, exist_ok=True)
    line = ""
    for arg in sys.argv[1:]:
        line = "%s %s" % (line, arg)
    pid_file = os.path.join(configDir, "discover_overlay.pid")
    rpc_file = os.path.join(configDir, "discover_overlay.rpc")
    try:
        with pidfile.PIDFile(pid_file):
            logging.getLogger().setLevel(logging.INFO)
            Discover(rpc_file, line)
    except pidfile.AlreadyRunningError:
        logging.warn("Discover overlay is currently running")

        with open(rpc_file, "w") as tfile:
            tfile.write(line)
            logging.warn("Sent RPC command")

