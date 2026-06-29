import Cocoa
import FlutterMacOS

class MainFlutterWindow: NSWindow {
  override func awakeFromNib() {
    let flutterViewController = FlutterViewController()
    let windowFrame = self.frame

    // Modern unified titlebar: native traffic lights float over Flutter content.
    self.titlebarAppearsTransparent = true
    self.titleVisibility = .hidden
    self.styleMask.insert(.fullSizeContentView)
    if #available(macOS 11.0, *) {
      self.toolbarStyle = .unified
    }
    self.toolbar = NSToolbar(identifier: "TrackStateToolbar")
    self.toolbar?.showsBaselineSeparator = false

    self.contentViewController = flutterViewController
    self.setFrame(windowFrame, display: true)

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()
  }
}
