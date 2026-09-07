Sign the macOS binary with a Developer ID certificate and notarize it, so
Gatekeeper no longer blocks it when it is downloaded in a browser.  The
``xattr -d com.apple.quarantine`` workaround is no longer needed.
