#!/usr/bin/env python3
# CueKeeperApp.py — Native macOS window (WKWebView) hosting the CueKeeper UI.
# Runs on top of the bundled Python venv; not a browser tab.
import sys

from Cocoa import (
    NSApplication,
    NSWindow,
    NSMakeRect,
    NSBackingStoreBuffered,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
)
from WebKit import WKWebView

APP_TITLE = "CueKeeper"
WINDOW_WIDTH = 1150
WINDOW_HEIGHT = 820
URL = "http://127.0.0.1:8000/"


class CueKeeperApp:
    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(0)  # NSApplicationActivationPolicyRegular

        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_(APP_TITLE)
        self.window.center()
        self.window.setReleasedWhenClosed_(True)

        self.webView = WKWebView.alloc().initWithFrame_(
            self.window.contentView().bounds()
        )
        self.webView.setAutoresizingMask_(  # width | height
            1 << 0 | 1 << 1
        )
        self.window.contentView().addSubview_(self.webView)

        self.window.makeKeyAndOrderFront_(None)
        self.app.activateIgnoringOtherApps_(True)

        from Foundation import NSURL, NSURLRequest

        url = NSURL.URLWithString_(URL)
        self.webView.loadRequest_(NSURLRequest.requestWithURL_(url))

    def run(self):
        self.app.run()


def main():
    app = CueKeeperApp()
    app.run()


if __name__ == "__main__":
    main()
