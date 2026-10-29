"""macOS Accessibility check. Prompting adds this app to the Accessibility list so the user can tick it."""
import sys


def accessibility_trusted(prompt: bool = True) -> bool:
    if sys.platform != "darwin":
        return True
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))
