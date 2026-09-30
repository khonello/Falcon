pragma Singleton

// THE RESULT OF SOMETHING YOU DID (docs/UI-COMPONENTS.md, `message`). Anywhere in the console can say
// it; `Toast` in the shell is the one place it is drawn. Good news is grey -- only the two hues that
// mean somebody must act are spent on colour (docs/UI.md).
import QtQuick

QtObject {
    signal posted(string text, string kind)
    // `message` is the result of something YOU did. `notification` is something that arrived on its
    // own -- a ping, a report, being blocked -- so it carries who it is about and waits to be read.
    signal arrived(string title, string text, string kind)

    function ok(text)     { posted(text, "note") }
    function warn(text)   { posted(text, "warn") }
    function failed(text) { posted(text, "danger") }

    function news(title, text)    { arrived(title, text, "note") }
    function urgent(title, text)  { arrived(title, text, "danger") }
}
