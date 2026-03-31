import Cocoa
import QuartzCore

let W: CGFloat = 540
let H: CGFloat = 460

class SetupWindow: NSWindow, NSTextFieldDelegate {
    var apiKeyField: NSTextField!
    var progressBar: NSProgressIndicator!
    var statusLabel: NSTextField!
    var resourceDir: String = ""
    var appIcon: NSImage?
    var hasKey: Bool = false

    func setup(resDir: String) {
        resourceDir = resDir
        setContentSize(NSSize(width: W, height: H))
        styleMask = [.titled, .closable, .fullSizeContentView]
        titlebarAppearsTransparent = true
        titleVisibility = .hidden
        isMovableByWindowBackground = true
        backgroundColor = NSColor(red: 0.10, green: 0.10, blue: 0.12, alpha: 1)
        center()

        // App icon
        let iconPath = resDir + "/AppIcon.icns"
        if FileManager.default.fileExists(atPath: iconPath) {
            appIcon = NSImage(contentsOfFile: iconPath)
        }

        // Enable paste (Cmd+V) — add Edit menu
        let mainMenu = NSMenu()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        let editMenuItem = NSMenuItem(title: "Edit", action: nil, keyEquivalent: "")
        editMenuItem.submenu = editMenu
        mainMenu.addItem(editMenuItem)
        NSApp.mainMenu = mainMenu

        // Check if key already exists
        let configPath = NSHomeDirectory() + "/.live-translator.json"
        if let data = try? Data(contentsOf: URL(fileURLWithPath: configPath)),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let key = json["openai_api_key"] as? String, !key.isEmpty {
            hasKey = true
            showStep2()  // Key exists, skip to installation
        } else {
            showStep1()
        }
    }

    func clear() { contentView?.subviews.forEach { $0.removeFromSuperview() } }

    // ─── Helpers ───

    func lbl(_ frame: NSRect, _ text: String, size: CGFloat = 14, weight: NSFont.Weight = .regular,
             color: NSColor = .white, align: NSTextAlignment = .center) -> NSTextField {
        let l = NSTextField(frame: frame)
        l.stringValue = text; l.isBezeled = false; l.drawsBackground = false
        l.isEditable = false; l.isSelectable = false; l.textColor = color
        l.font = NSFont.systemFont(ofSize: size, weight: weight)
        l.alignment = align; l.lineBreakMode = .byWordWrapping; l.maximumNumberOfLines = 0
        return l
    }

    func stepBadge(_ step: Int, total: Int = 3) -> NSView {
        let v = NSView(frame: NSRect(x: (W-90)/2, y: H-48, width: 90, height: 24))
        v.wantsLayer = true
        v.layer?.backgroundColor = NSColor(white: 1, alpha: 0.05).cgColor
        v.layer?.cornerRadius = 12
        v.layer?.borderWidth = 0.5
        v.layer?.borderColor = NSColor(white: 1, alpha: 0.1).cgColor
        v.addSubview(lbl(NSRect(x: 0, y: 2, width: 90, height: 18),
                         "STEP \(step) / \(total)", size: 10, weight: .bold,
                         color: NSColor(white: 0.45, alpha: 1)))
        return v
    }

    func appIconView(_ y: CGFloat, size: CGFloat = 64) -> NSImageView {
        let iv = NSImageView(frame: NSRect(x: (W-size)/2, y: y, width: size, height: size))
        if let icon = appIcon { iv.image = icon }
        iv.imageScaling = .scaleProportionallyUpOrDown
        iv.wantsLayer = true
        iv.layer?.cornerRadius = size * 0.22
        iv.layer?.masksToBounds = true
        iv.layer?.borderWidth = 1
        iv.layer?.borderColor = NSColor(white: 1, alpha: 0.08).cgColor
        return iv
    }

    func sep(_ y: CGFloat) -> NSView {
        let v = NSView(frame: NSRect(x: 50, y: y, width: W-100, height: 1))
        v.wantsLayer = true
        v.layer?.backgroundColor = NSColor(white: 1, alpha: 0.06).cgColor
        return v
    }

    func greenBtn(_ frame: NSRect, _ title: String, action: Selector) -> NSView {
        let bg = NSView(frame: frame)
        bg.wantsLayer = true
        bg.layer?.backgroundColor = NSColor(red: 0.22, green: 0.58, blue: 0.36, alpha: 1).cgColor
        bg.layer?.cornerRadius = frame.height / 2
        let btn = NSButton(frame: NSRect(x: 0, y: 0, width: frame.width, height: frame.height))
        btn.title = title; btn.isBordered = false
        btn.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        btn.contentTintColor = .white; btn.target = self; btn.action = action
        bg.addSubview(btn)
        return bg
    }

    func ghostBtn(_ frame: NSRect, _ title: String, action: Selector) -> NSButton {
        let btn = NSButton(frame: frame)
        btn.title = title; btn.isBordered = false
        btn.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        btn.contentTintColor = NSColor(white: 0.4, alpha: 1)
        btn.target = self; btn.action = action
        return btn
    }

    // ═══════════════════════════════════════
    // MARK: Step 1 — API Key
    // ═══════════════════════════════════════
    func showStep1() {
        clear()
        guard let cv = contentView else { return }

        cv.addSubview(stepBadge(1))
        cv.addSubview(appIconView(H - 130))

        cv.addSubview(lbl(NSRect(x: 30, y: H-180, width: W-60, height: 35),
                          "Welcome to Live Translator", size: 24, weight: .bold))

        cv.addSubview(lbl(NSRect(x: 50, y: H-225, width: W-100, height: 34),
                          "Translate any audio playing on your Mac in real-time.\nEnter your OpenAI API key to get started.",
                          size: 13, weight: .regular, color: NSColor(white: 0.45, alpha: 1)))

        cv.addSubview(sep(H - 245))

        // Label
        cv.addSubview(lbl(NSRect(x: 55, y: H-275, width: 200, height: 18),
                          "OpenAI API Key", size: 12, weight: .semibold,
                          color: NSColor(white: 0.55, alpha: 1), align: .left))

        // Input — regular NSTextField (not secure) so paste works naturally
        apiKeyField = NSTextField(frame: NSRect(x: 52, y: H-315, width: W-104, height: 32))
        apiKeyField.placeholderString = "sk-proj-..."
        apiKeyField.font = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        apiKeyField.textColor = NSColor(white: 0.85, alpha: 1)
        apiKeyField.backgroundColor = NSColor(red: 0.14, green: 0.14, blue: 0.16, alpha: 1)
        apiKeyField.isBezeled = true
        apiKeyField.bezelStyle = .roundedBezel
        apiKeyField.focusRingType = .none
        apiKeyField.wantsLayer = true
        apiKeyField.layer?.cornerRadius = 8
        apiKeyField.layer?.borderWidth = 1
        apiKeyField.layer?.borderColor = NSColor(white: 1, alpha: 0.1).cgColor
        cv.addSubview(apiKeyField)

        // Link
        cv.addSubview(lbl(NSRect(x: 55, y: H-340, width: W-110, height: 15),
                          "Get your key at platform.openai.com →", size: 11, weight: .regular,
                          color: NSColor(red: 0.35, green: 0.65, blue: 0.5, alpha: 0.8), align: .left))

        // Buttons
        cv.addSubview(ghostBtn(NSRect(x: 45, y: 25, width: 70, height: 36), "Quit", action: #selector(onQuit)))
        cv.addSubview(greenBtn(NSRect(x: W-170, y: 22, width: 130, height: 42), "Next →", action: #selector(onNext1)))
    }

    @objc func onNext1() {
        let key = apiKeyField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard key.count >= 10 else {
            // Shake
            let cx = apiKeyField.frame.origin.x + apiKeyField.frame.width / 2
            let anim = CAKeyframeAnimation(keyPath: "position.x")
            anim.values = [cx, cx-10, cx+10, cx-5, cx+5, cx] as [NSNumber]
            anim.duration = 0.4
            apiKeyField.layer?.add(anim, forKey: "shake")
            apiKeyField.layer?.borderColor = NSColor.red.withAlphaComponent(0.5).cgColor
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                self.apiKeyField.layer?.borderColor = NSColor(white: 1, alpha: 0.1).cgColor
            }
            return
        }

        // Save config
        let config: [String: Any] = [
            "openai_api_key": key, "source_locale": "en-US", "target_lang": "tr",
            "model": "gpt-4o-mini", "tts_provider": "piper", "tts_voice": "nova", "tts_speed": 1.0
        ]
        if let data = try? JSONSerialization.data(withJSONObject: config, options: .prettyPrinted) {
            try? data.write(to: URL(fileURLWithPath: NSHomeDirectory() + "/.live-translator.json"))
        }
        showStep2()
    }

    // ═══════════════════════════════════════
    // MARK: Step 2 — Installing
    // ═══════════════════════════════════════
    func showStep2() {
        clear()
        guard let cv = contentView else { return }

        cv.addSubview(stepBadge(2))
        cv.addSubview(appIconView(H - 130))

        cv.addSubview(lbl(NSRect(x: 30, y: H-180, width: W-60, height: 35),
                          "Setting up...", size: 24, weight: .bold))

        cv.addSubview(lbl(NSRect(x: 50, y: H-215, width: W-100, height: 30),
                          "Installing packages and downloading voice models.\nThis only happens once.",
                          size: 13, weight: .regular, color: NSColor(white: 0.42, alpha: 1)))

        cv.addSubview(sep(H - 235))

        // Progress track
        let trackBg = NSView(frame: NSRect(x: 55, y: H-268, width: W-110, height: 8))
        trackBg.wantsLayer = true
        trackBg.layer?.backgroundColor = NSColor(white: 1, alpha: 0.05).cgColor
        trackBg.layer?.cornerRadius = 4
        cv.addSubview(trackBg)

        progressBar = NSProgressIndicator(frame: NSRect(x: 55, y: H-268, width: W-110, height: 8))
        progressBar.style = .bar; progressBar.minValue = 0; progressBar.maxValue = 100
        progressBar.doubleValue = 0; progressBar.isIndeterminate = false
        progressBar.wantsLayer = true; progressBar.layer?.cornerRadius = 4
        cv.addSubview(progressBar)

        statusLabel = lbl(NSRect(x: 55, y: H-292, width: W-110, height: 16),
                          "Preparing...", size: 11, weight: .medium,
                          color: NSColor(white: 0.38, alpha: 1))
        cv.addSubview(statusLabel)

        // Checklist
        let items = ["Python environment", "Required packages", "Voice models (~580MB)"]
        for (i, item) in items.enumerated() {
            let y = H - CGFloat(328 + i * 32)
            let dot = lbl(NSRect(x: 70, y: y, width: 20, height: 22), "○",
                          size: 16, weight: .ultraLight, color: NSColor(white: 0.22, alpha: 1))
            dot.tag = 100 + i
            cv.addSubview(dot)
            let text = lbl(NSRect(x: 95, y: y + 1, width: W-160, height: 20), item,
                           size: 13, weight: .regular, color: NSColor(white: 0.38, alpha: 1), align: .left)
            text.tag = 200 + i
            cv.addSubview(text)
        }

        DispatchQueue.global().async { self.doInstall() }
    }

    func setProgress(_ val: Double, _ text: String) {
        DispatchQueue.main.async {
            self.progressBar?.doubleValue = val
            self.statusLabel?.stringValue = text
        }
    }

    func checkItem(_ index: Int) {
        DispatchQueue.main.async {
            guard let cv = self.contentView else { return }
            if let dot = cv.viewWithTag(100 + index) as? NSTextField {
                dot.stringValue = "✓"
                dot.textColor = NSColor(red: 0.35, green: 0.78, blue: 0.48, alpha: 1)
                dot.font = NSFont.systemFont(ofSize: 14, weight: .bold)
            }
            if let text = cv.viewWithTag(200 + index) as? NSTextField {
                text.textColor = NSColor(white: 0.6, alpha: 1)
            }
        }
    }

    func doInstall() {
        let supportDir = NSHomeDirectory() + "/Library/Application Support/LiveTranslator"
        try? FileManager.default.createDirectory(atPath: supportDir, withIntermediateDirectories: true)
        let venv = supportDir + "/venv"
        let log = NSHomeDirectory() + "/Library/Logs/LiveTranslator.log"

        // Find python3
        let pythonPaths = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
        var python = pythonPaths.first { FileManager.default.fileExists(atPath: $0) }

        // No python found — install via Homebrew
        if python == nil {
            setProgress(2, "Python not found, installing...")

            // Check if Homebrew exists
            let brewPaths = ["/opt/homebrew/bin/brew", "/usr/local/bin/brew"]
            let brew = brewPaths.first { FileManager.default.fileExists(atPath: $0) }

            if let brew = brew {
                // Install Python via Homebrew
                shell([brew, "install", "python@3.13"], log)
                python = "/opt/homebrew/bin/python3"
                if !FileManager.default.fileExists(atPath: python!) {
                    python = "/usr/local/bin/python3"
                }
            } else {
                // Install Homebrew first, then Python
                setProgress(1, "Installing Homebrew...")
                shell(["/bin/bash", "-c",
                       "NONINTERACTIVE=1 /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""],
                      log)

                let newBrew = brewPaths.first { FileManager.default.fileExists(atPath: $0) }
                if let newBrew = newBrew {
                    setProgress(2, "Installing Python...")
                    shell([newBrew, "install", "python@3.13"], log)
                    python = "/opt/homebrew/bin/python3"
                }
            }

            // Final check
            if python == nil || !FileManager.default.fileExists(atPath: python!) {
                DispatchQueue.main.async {
                    self.showError("Python 3.11+ is required but could not be installed.\n\nPlease install manually:\n  brew install python\n\nOr download from python.org")
                }
                return
            }
        }

        let pythonBin = python!

        setProgress(5, "Creating Python environment...")
        shell([pythonBin, "-m", "venv", venv], log)
        checkItem(0)
        setProgress(20, "Environment ready")
        Thread.sleep(forTimeInterval: 0.3)

        setProgress(25, "Installing packages...")
        let pip = venv + "/bin/pip"
        let req = resourceDir + "/requirements.txt"
        shell([pip, "install", "-q", "-r", req], log)
        checkItem(1)
        setProgress(60, "Packages installed")
        Thread.sleep(forTimeInterval: 0.3)

        setProgress(65, "Downloading voice models...")
        let dl = resourceDir + "/scripts/download_models.sh"
        if FileManager.default.fileExists(atPath: dl) {
            shell(["/bin/bash", dl], log, cwd: resourceDir)
        }
        checkItem(2)
        setProgress(100, "All done!")

        Thread.sleep(forTimeInterval: 0.5)
        DispatchQueue.main.async { self.showStep3() }
    }

    func shell(_ args: [String], _ log: String, cwd: String? = nil) {
        // Use /bin/bash -c with properly quoted args — most reliable
        let quoted = args.map { "'\($0.replacingOccurrences(of: "'", with: "'\\''"))'" }.joined(separator: " ")
        var cmd = quoted
        if let dir = cwd {
            cmd = "cd '\(dir)' && \(quoted)"
        }
        cmd += " >> '\(log)' 2>&1"

        let t = Process()
        t.launchPath = "/bin/bash"
        t.arguments = ["-c", cmd]
        do {
            try t.run()
            t.waitUntilExit()
        } catch {
            // Log error
            let errMsg = "Shell error: \(error)\nCommand: \(cmd)\n"
            if let data = errMsg.data(using: .utf8) {
                let fh = FileHandle(forWritingAtPath: log) ?? {
                    FileManager.default.createFile(atPath: log, contents: nil)
                    return FileHandle(forWritingAtPath: log)!
                }()
                fh.seekToEndOfFile()
                fh.write(data)
                fh.closeFile()
            }
        }
    }

    // ═══════════════════════════════════════
    // MARK: Step 3 — Ready
    // ═══════════════════════════════════════
    func showStep3() {
        clear()
        guard let cv = contentView else { return }

        cv.addSubview(stepBadge(3))
        cv.addSubview(appIconView(H - 135, size: 72))

        cv.addSubview(lbl(NSRect(x: 30, y: H-190, width: W-60, height: 38),
                          "You're all set!", size: 28, weight: .bold,
                          color: NSColor(red: 0.4, green: 0.82, blue: 0.52, alpha: 1)))

        cv.addSubview(sep(H - 205))

        cv.addSubview(lbl(NSRect(x: 50, y: H-280, width: W-100, height: 60),
                          "Live Translator is ready.\n\nPlay any audio on your Mac and translations\nwill appear in the floating panel.\n\nYou can change settings anytime from the panel.",
                          size: 13, weight: .regular, color: NSColor(white: 0.48, alpha: 1)))

        cv.addSubview(greenBtn(NSRect(x: (W-170)/2, y: 30, width: 170, height: 46),
                               "Launch →", action: #selector(onLaunch)))
    }

    func showError(_ message: String) {
        clear()
        guard let cv = contentView else { return }

        cv.addSubview(appIconView(H - 130))
        cv.addSubview(lbl(NSRect(x: 30, y: H-175, width: W-60, height: 35),
                          "Setup Failed", size: 24, weight: .bold,
                          color: NSColor(red: 0.9, green: 0.3, blue: 0.3, alpha: 1)))
        cv.addSubview(sep(H - 190))
        cv.addSubview(lbl(NSRect(x: 50, y: H-290, width: W-100, height: 80),
                          message, size: 13, weight: .regular,
                          color: NSColor(white: 0.5, alpha: 1)))
        cv.addSubview(ghostBtn(NSRect(x: (W-80)/2, y: 30, width: 80, height: 36),
                               "Quit", action: #selector(onQuit)))
    }

    @objc func onLaunch() {
        // Write marker file — launcher reads this
        let marker = "/tmp/.livetranslator_launch"
        try? "LAUNCH".write(toFile: marker, atomically: true, encoding: .utf8)
        // Verify
        if FileManager.default.fileExists(atPath: marker) {
            exit(0)
        }
        exit(0)
    }

    @objc func onQuit() {
        exit(1)
    }
}

// ═══ Main ═══
let args = CommandLine.arguments
let resDir = args.count > 1 ? args[1] : FileManager.default.currentDirectoryPath
let configPath = NSHomeDirectory() + "/.live-translator.json"
let venvPath = NSHomeDirectory() + "/Library/Application Support/LiveTranslator/venv"

// Check if BOTH config and venv exist
var needsSetup = true
if FileManager.default.fileExists(atPath: configPath),
   FileManager.default.fileExists(atPath: venvPath + "/bin/python"),
   let data = try? Data(contentsOf: URL(fileURLWithPath: configPath)),
   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
   let key = json["openai_api_key"] as? String, !key.isEmpty {
    needsSetup = false
}

if !needsSetup { print("LAUNCH"); exit(0) }

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let win = SetupWindow(contentRect: .zero, styleMask: [.titled, .closable, .fullSizeContentView],
                      backing: .buffered, defer: false)
win.setup(resDir: resDir)
win.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: true)
app.run()
