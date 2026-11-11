/*
==================================================
 WebEye Universal Virtual Keyboard
==================================================
*/


(function () {

    "use strict";


    /*
    ------------------------------------------------
    Prevent duplicate installation
    ------------------------------------------------
    */

    if (window.__WEBEYE_KEYBOARD_LOADED__) {

        return;

    }

    window.__WEBEYE_KEYBOARD_LOADED__ = true;


    /*
    ------------------------------------------------
    Variables
    ------------------------------------------------
    */

    let activeElement = null;

    let shiftEnabled = false;

    let keyboardVisible = false;


    /*
    ------------------------------------------------
    Create keyboard
    ------------------------------------------------
    */

    const keyboard =
        document.createElement("div");

    keyboard.id =
        "webeye-virtual-keyboard";


    /*
    ------------------------------------------------
    Keyboard HTML
    ------------------------------------------------
    */

    keyboard.innerHTML = `

        <div class="webeye-keyboard-header">

            <div>

                <div class="webeye-keyboard-title">
                    WebEye Virtual Keyboard
                </div>

                <div
                    class="webeye-keyboard-status"
                    id="webeye-status">

                    Ready for typing

                </div>

            </div>


            <button
                class="webeye-close"
                id="webeye-close">

                ×

            </button>

        </div>


        <div
            class="webeye-display"
            id="webeye-display">

            Start typing...

        </div>


        <!-- Numbers -->

        <div class="webeye-keyboard-row">

            <button class="webeye-key" data-key="1">1</button>
            <button class="webeye-key" data-key="2">2</button>
            <button class="webeye-key" data-key="3">3</button>
            <button class="webeye-key" data-key="4">4</button>
            <button class="webeye-key" data-key="5">5</button>
            <button class="webeye-key" data-key="6">6</button>
            <button class="webeye-key" data-key="7">7</button>
            <button class="webeye-key" data-key="8">8</button>
            <button class="webeye-key" data-key="9">9</button>
            <button class="webeye-key" data-key="0">0</button>

        </div>


        <!-- QWERTY -->

        <div class="webeye-keyboard-row">

            <button class="webeye-key" data-key="q">Q</button>
            <button class="webeye-key" data-key="w">W</button>
            <button class="webeye-key" data-key="e">E</button>
            <button class="webeye-key" data-key="r">R</button>
            <button class="webeye-key" data-key="t">T</button>
            <button class="webeye-key" data-key="y">Y</button>
            <button class="webeye-key" data-key="u">U</button>
            <button class="webeye-key" data-key="i">I</button>
            <button class="webeye-key" data-key="o">O</button>
            <button class="webeye-key" data-key="p">P</button>

        </div>


        <!-- ASDF -->

        <div class="webeye-keyboard-row">

            <button class="webeye-key" data-key="a">A</button>
            <button class="webeye-key" data-key="s">S</button>
            <button class="webeye-key" data-key="d">D</button>
            <button class="webeye-key" data-key="f">F</button>
            <button class="webeye-key" data-key="g">G</button>
            <button class="webeye-key" data-key="h">H</button>
            <button class="webeye-key" data-key="j">J</button>
            <button class="webeye-key" data-key="k">K</button>
            <button class="webeye-key" data-key="l">L</button>

        </div>


        <!-- ZXCV -->

        <div class="webeye-keyboard-row">

            <button
                class="webeye-key webeye-special webeye-shift"
                id="webeye-shift">

                ⇧ Shift

            </button>


            <button class="webeye-key" data-key="z">Z</button>
            <button class="webeye-key" data-key="x">X</button>
            <button class="webeye-key" data-key="c">C</button>
            <button class="webeye-key" data-key="v">V</button>
            <button class="webeye-key" data-key="b">B</button>
            <button class="webeye-key" data-key="n">N</button>
            <button class="webeye-key" data-key="m">M</button>


            <button
                class="webeye-key webeye-special webeye-backspace"
                id="webeye-backspace">

                ⌫

            </button>

        </div>


        <!-- Bottom -->

        <div class="webeye-keyboard-row">

            <button
                class="webeye-key webeye-special"
                data-key=".">

                .

            </button>


            <button
                class="webeye-key webeye-special"
                data-key=",">

                ,

            </button>


            <button
                class="webeye-key webeye-special"
                data-key="@">

                @

            </button>


            <button
                class="webeye-key webeye-space"
                id="webeye-space">

                SPACE

            </button>


            <button
                class="webeye-key webeye-clear"
                id="webeye-clear">

                CLEAR

            </button>


            <button
                class="webeye-key webeye-enter"
                id="webeye-enter">

                ENTER ↵

            </button>

        </div>

    `;


    /*
    ------------------------------------------------
    Add keyboard to webpage
    ------------------------------------------------
    */

    document.documentElement.appendChild(keyboard);


    keyboard.style.display =
        "none";


    /*
    ------------------------------------------------
    Get elements
    ------------------------------------------------
    */

    const display =
        keyboard.querySelector(
            "#webeye-display"
        );


    const status =
        keyboard.querySelector(
            "#webeye-status"
        );


    const shiftButton =
        keyboard.querySelector(
            "#webeye-shift"
        );


    const backspaceButton =
        keyboard.querySelector(
            "#webeye-backspace"
        );


    const spaceButton =
        keyboard.querySelector(
            "#webeye-space"
        );


    const clearButton =
        keyboard.querySelector(
            "#webeye-clear"
        );


    const enterButton =
        keyboard.querySelector(
            "#webeye-enter"
        );


    const closeButton =
        keyboard.querySelector(
            "#webeye-close"
        );


    /*
    ==================================================
    Detect editable element
    ==================================================
    */

    function getEditableElement(element) {

        if (!element) {

            return null;

        }


        /*
        INPUT
        */

        if (
            element.tagName === "INPUT"
        ) {

            const type =
                (
                    element.type || "text"
                ).toLowerCase();


            const allowedTypes = [
                "text",
                "search",
                "email",
                "url",
                "tel",
                "number",
                "password"
            ];


            if (
                allowedTypes.includes(type)
            ) {

                return element;

            }

        }


        /*
        TEXTAREA
        */

        if (
            element.tagName === "TEXTAREA"
        ) {

            return element;

        }


        /*
        CONTENTEDITABLE
        */

        if (
            element.isContentEditable
        ) {

            return element;

        }


        /*
        ARIA textbox
        */

        if (
            element.getAttribute &&
            element.getAttribute("role")
            === "textbox"
        ) {

            return element;

        }


        /*
        Parent editable element
        */

        if (element.parentElement) {

            return getEditableElement(
                element.parentElement
            );

        }


        return null;

    }


    /*
    ==================================================
    Focus detection
    ==================================================
    */

    document.addEventListener(
        "focusin",
        function (event) {

            const editable =
                getEditableElement(
                    event.target
                );


            if (!editable) {

                return;

            }


            /*
            Ignore the virtual keyboard itself
            */

            if (
                keyboard.contains(editable)
            ) {

                return;

            }


            activeElement =
                editable;


            shiftEnabled = false;

            shiftButton.classList.remove(
                "webeye-active"
            );


            updateDisplay();

            showKeyboard();

        },
        true
    );


    /*
    ==================================================
    Also detect mouse click
    ==================================================
    */

    document.addEventListener(
        "click",
        function (event) {

            const editable =
                getEditableElement(
                    event.target
                );


            if (!editable) {

                return;

            }


            if (
                keyboard.contains(editable)
            ) {

                return;

            }


            activeElement =
                editable;


            updateDisplay();

            showKeyboard();

        },
        true
    );


    /*
    ==================================================
    Show keyboard
    ==================================================
    */

    function showKeyboard() {

        keyboard.style.display =
            "block";


        keyboardVisible =
            true;


        status.textContent =
            "Ready for typing";

    }


    /*
    ==================================================
    Hide keyboard
    ==================================================
    */

    function hideKeyboard() {

        keyboard.style.display =
            "none";


        keyboardVisible =
            false;

    }


    /*
    ==================================================
    Get current text
    ==================================================
    */

    function getCurrentValue() {

        if (!activeElement) {

            return "";

        }


        if (
            activeElement.isContentEditable
        ) {

            return activeElement.innerText || "";

        }


        return activeElement.value || "";

    }


    /*
    ==================================================
    Update display
    ==================================================
    */

    function updateDisplay() {

        const value =
            getCurrentValue();


        if (value.length === 0) {

            display.textContent =
                "Start typing...";

        } else {

            display.textContent =
                value;

        }

    }


    /*
    ==================================================
    Set input value
    ==================================================
    */

    function setInputValue(
        element,
        value
    ) {

        if (!element) {

            return;

        }


        /*
        Contenteditable
        */

        if (
            element.isContentEditable
        ) {

            element.textContent =
                value;


            element.dispatchEvent(
                new InputEvent(
                    "input",
                    {
                        bubbles: true,
                        inputType:
                            "insertText",
                        data: value
                    }
                )
            );


            return;

        }


        /*
        React/Vue compatible
        */

        const prototype =
            Object.getPrototypeOf(
                element
            );


        const descriptor =
            Object.getOwnPropertyDescriptor(
                prototype,
                "value"
            );


        if (
            descriptor &&
            descriptor.set
        ) {

            descriptor.set.call(
                element,
                value
            );

        } else {

            element.value =
                value;

        }


        /*
        Notify website
        */

        element.dispatchEvent(
            new Event(
                "input",
                {
                    bubbles: true
                }
            )
        );


        element.dispatchEvent(
            new Event(
                "change",
                {
                    bubbles: true
                }
            )
        );

    }


    /*
    ==================================================
    Insert character
    ==================================================
    */

    function insertCharacter(
        character
    ) {

        if (!activeElement) {

            return;

        }


        /*
        Contenteditable
        */

        if (
            activeElement.isContentEditable
        ) {

            document.execCommand(
                "insertText",
                false,
                character
            );


            updateDisplay();

            return;

        }


        /*
        Standard input
        */

        const value =
            activeElement.value || "";


        const start =
            activeElement.selectionStart
            ?? value.length;


        const end =
            activeElement.selectionEnd
            ?? value.length;


        let newCharacter =
            character;


        if (shiftEnabled) {

            newCharacter =
                character.toUpperCase();

        }


        const newValue =
            value.slice(
                0,
                start
            )
            +
            newCharacter
            +
            value.slice(
                end
            );


        setInputValue(
            activeElement,
            newValue
        );


        const newPosition =
            start +
            newCharacter.length;


        try {

            activeElement.setSelectionRange(
                newPosition,
                newPosition
            );

        } catch (error) {

            // Some input types do not support selection.

        }


        updateDisplay();


        status.textContent =
            "Typing...";

    }


    /*
    ==================================================
    Backspace
    ==================================================
    */

    function performBackspace() {

        if (!activeElement) {

            return;

        }


        if (
            activeElement.isContentEditable
        ) {

            document.execCommand(
                "delete"
            );


            updateDisplay();

            return;

        }


        const value =
            activeElement.value || "";


        const start =
            activeElement.selectionStart
            ?? value.length;


        const end =
            activeElement.selectionEnd
            ?? value.length;


        let newStart =
            start;


        let newValue;


        if (
            start !== end
        ) {

            newValue =
                value.slice(
                    0,
                    start
                )
                +
                value.slice(
                    end
                );

        } else if (
            start > 0
        ) {

            newStart =
                start - 1;


            newValue =
                value.slice(
                    0,
                    start - 1
                )
                +
                value.slice(
                    end
                );

        } else {

            return;

        }


        setInputValue(
            activeElement,
            newValue
        );


        try {

            activeElement.setSelectionRange(
                newStart,
                newStart
            );

        } catch (error) {

        }


        updateDisplay();


        status.textContent =
            "Backspace";

    }


    /*
    ==================================================
    Space
    ==================================================
    */

    function performSpace() {

        insertCharacter(" ");

    }


    /*
    ==================================================
    Clear
    ==================================================
    */

    function performClear() {

        if (!activeElement) {

            return;

        }


        setInputValue(
            activeElement,
            ""
        );


        updateDisplay();


        status.textContent =
            "Text cleared";

    }


    /*
    ==================================================
    Enter
    ==================================================
    */

    function performEnter() {

        if (!activeElement) {

            return;

        }


        /*
        Try normal keyboard event
        */

        activeElement.dispatchEvent(
            new KeyboardEvent(
                "keydown",
                {
                    key: "Enter",
                    code: "Enter",
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                }
            )
        );


        /*
        Search forms
        */

        const form =
            activeElement.closest(
                "form"
            );


        if (form) {

            try {

                if (
                    typeof form.requestSubmit
                    === "function"
                ) {

                    form.requestSubmit();

                } else {

                    form.submit();

                }

            } catch (error) {

                // Ignore websites that block submission.

            }

        } else {

            /*
            Try clicking nearby search button.
            */

            const parent =
                activeElement.parentElement;


            if (parent) {

                const button =
                    parent.querySelector(
                        'button[type="submit"], input[type="submit"]'
                    );


                if (button) {

                    button.click();

                }

            }

        }


        status.textContent =
            "Enter pressed";


        /*
        Hide after search
        */

        setTimeout(
            function () {

                hideKeyboard();

            },
            300
        );

    }


    /*
    ==================================================
    Shift
    ==================================================
    */

    shiftButton.addEventListener(
        "mousedown",
        function (event) {

            event.preventDefault();

        }
    );


    shiftButton.addEventListener(
        "click",
        function () {

            shiftEnabled =
                !shiftEnabled;


            if (shiftEnabled) {

                shiftButton.classList.add(
                    "webeye-active"
                );


                status.textContent =
                    "Shift ON";

            } else {

                shiftButton.classList.remove(
                    "webeye-active"
                );


                status.textContent =
                    "Shift OFF";

            }

        }
    );


    /*
    ==================================================
    Normal keys
    ==================================================
    */

    keyboard
        .querySelectorAll(
            "[data-key]"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "mousedown",
                    function (event) {

                        /*
                        Important:
                        Don't let button click
                        steal focus from input.
                        */

                        event.preventDefault();

                    }
                );


                button.addEventListener(
                    "click",
                    function () {

                        const key =
                            this.getAttribute(
                                "data-key"
                            );


                        insertCharacter(
                            key
                        );

                    }
                );

            }
        );


    /*
    ==================================================
    Backspace button
    ==================================================
    */

    backspaceButton.addEventListener(
        "mousedown",
        function (event) {

            event.preventDefault();

        }
    );


    backspaceButton.addEventListener(
        "click",
        performBackspace
    );


    /*
    ==================================================
    Space button
    ==================================================
    */

    spaceButton.addEventListener(
        "mousedown",
        function (event) {

            event.preventDefault();

        }
    );


    spaceButton.addEventListener(
        "click",
        performSpace
    );


    /*
    ==================================================
    Clear button
    ==================================================
    */

    clearButton.addEventListener(
        "mousedown",
        function (event) {

            event.preventDefault();

        }
    );


    clearButton.addEventListener(
        "click",
        performClear
    );


    /*
    ==================================================
    Enter button
    ==================================================
    */

    enterButton.addEventListener(
        "mousedown",
        function (event) {

            event.preventDefault();

        }
    );


    enterButton.addEventListener(
        "click",
        performEnter
    );


    /*
    ==================================================
    Close button
    ==================================================
    */

    closeButton.addEventListener(
        "mousedown",
        function (event) {

            event.preventDefault();

        }
    );


    closeButton.addEventListener(
        "click",
        function () {

            hideKeyboard();


            status.textContent =
                "Keyboard closed";

        }
    );


    /*
    ==================================================
    Keep active element
    ==================================================
    */

    document.addEventListener(
        "selectionchange",
        function () {

            if (
                document.activeElement
            ) {

                const editable =
                    getEditableElement(
                        document.activeElement
                    );


                if (editable) {

                    activeElement =
                        editable;

                }

            }

        }
    );


    /*
    ==================================================
    Debug message
    ==================================================
    */

    console.log(
        "WebEye Universal Virtual Keyboard loaded."
    );

})();