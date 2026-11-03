#!/usr/bin/env python3
# CueKeeperApp.py — Native macOS window (WKWebView) hosting CueKeeper.
#
# Polished app behavior:
#   * Auto-injects the access token into localStorage so the operator never
#     has to copy/paste it from a notification.
#   * Real macOS menu bar (CueKeeper: About / Quit, File: Close).
#   * Dark window background so there's no white "website" flash before the
#     UI loads.
#   * Properly sized, centered window with min size.
import os

from Cocoa import (
    NSApplication,
    NSWindow,
    NSMakeRect,
    NSBackingStoreBuffered,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSMenu,
    NSMenuItem,
    NSApplicationActivationPolicyRegular,
    NSColor,
)
from WebKit import WKWebView, WKWebViewConfiguration
from Foundation import NSObject, NSURL, NSURLRequest

TOKEN = os.environ.get("CUEKEEPER_TOKEN", "")
PORT = os.environ.get("CUEKEEPER_PORT", "8000")
URL = "http://127.0.0.1:%s/" % PORT


class NavigationDelegate(NSObject):
    """Injects the token after the page finishes loading."""

    def webView_didFinishNavigation_(self, webView, navigation):
        if not TOKEN:
            return
        # repr() emits a single-quoted string; the URL-safe token contains no
        # quotes, so this is safe to embed in a JS string literal.
        js = (
            "(function() {"
            "  localStorage.setItem('cuekeeper-token', %s);"
            "  if (typeof loadSavedToken === 'function') loadSavedToken();"
            "  if (typeof connectWebSocket === 'function') connectWebSocket();"
            "  if (typeof loadCues === 'function') loadCues();"
            "})();"
        ) % (repr(TOKEN),)
        webView.evaluateJavaScript_completionHandler_(js, None)


class CueKeeperApp:
    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        self._setup_menu()

        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 1200, 850), style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("CueKeeper")
        self.window.center()
        self.window.setReleasedWhenClosed_(True)
        self.window.setMinSize_(__import__("Foundation").NSMakeSize(800, 600))

        # Dark window background — no white flash before the UI paints.
        self.window.contentView().setWantsLayer_(True)
        dark = NSColor.colorWithRed_green_blue_alpha_(0.043, 0.047, 0.063, 1.0)
        self.window.contentView().layer().setBackgroundColor_(dark.CGColor())

        config = WKWebViewConfiguration.alloc().init()
        self.webView = WKWebView.alloc().initWithFrame_configuration_(
            self.window.contentView().bounds(), config
        )
        self.webView.setAutoresizingMask_(1 << 0 | 1 << 1)
        self.window.contentView().addSubview_(self.webView)

        delegate = NavigationDelegate.alloc().init()
        self.webView.setNavigationDelegate_(delegate)

        self.window.makeKeyAndOrderFront_(None)
        self.app.activateIgnoringOtherApps_(True)

        url = NSURL.URLWithString_(URL)
        self.webView.loadRequest_(NSURLRequest.requestWithURL_(url))

    def _setup_menu(self):
        main = NSMenu.alloc().initWithTitle_("CueKeeper")

        app_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("", None, "")
        app_sub = NSMenu.alloc().initWithTitle_("CueKeeper")
        app_sub.addItemWithTitle_action_keyEquivalent_(
            "About CueKeeper", "orderFrontStandardAboutPanel:", ""
        )
        app_sub.addItem_(NSMenuItem.separatorItem())
        app_sub.addItemWithTitle_action_keyEquivalent_("Quit CueKeeper", "terminate:", "q")
        app_item.setSubmenu_(app_sub)
        main.addItem_(app_item)

        file_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("File", None, "")
        file_sub = NSMenu.alloc().initWithTitle_("File")
        file_sub.addItemWithTitle_action_keyEquivalent_("Close Window", "performClose:", "w")
        file_item.setSubmenu_(file_sub)
        main.addItem_(file_item)

        self.app.setMainMenu_(main)

    def run(self):
        self.app.run()


def main():
    CueKeeperApp().run()


if __name__ == "__main__":
    main()
