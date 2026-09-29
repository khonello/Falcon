pragma Singleton

// THE RESULT OF SOMETHING YOU DID (docs/UI-COMPONENTS.md, `message`). Anywhere in the console can say
// it; `Toast` in the shell is the one place it is drawn. Good news is grey -- only the two hues that
// mean somebody must act are spent on colour (docs/UI.md).
import QtQuick

QtObject {
    signal posted(string text, string kind)

    function ok(text)     { posted(text, "note") }
    function warn(text)   { posted(text, "warn") }
    function failed(text) { posted(text, "danger") }
}
