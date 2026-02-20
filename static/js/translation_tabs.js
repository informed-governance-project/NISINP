window.addEventListener("load", function () {
    const fieldset = document.querySelector(".inline-group");
    if (!fieldset) return;

    const languages = window.AVAILABLE_LANGUAGES || [];
    if (!languages.length) return;

    const forms = Array.from(
        fieldset.querySelectorAll(".inline-related.dynamic-translations:not(.empty-form)")
    );

    // Map language → form existant
    // Handles both cases: editable input and read-only field (plain text)
    const langForms = {};
    forms.forEach(f => {
        // Case 1 : editable input
        const input = f.querySelector("input[name$='language_code']");
        if (input) {
            langForms[input.value] = f;
            return;
        }
        // Case 2 : readonly field — Django renders a <p> or span with the text
        const allRows = f.querySelectorAll(".form-row, .field-language_code");
        for (const row of allRows) {
            if (row.classList.contains("field-language_code")) {
                const text = row.querySelector(".readonly")?.textContent?.trim();
                if (text) {
                    langForms[text] = f;
                    return;
                }
            }
        }
    });

    function hideLangCodeField(form) {
        // editable
        const input = form.querySelector("input[name$='language_code']");
        if (input) {
            const row = input.closest(".form-row") || input.closest("p") || input.parentElement;
            if (row) row.style.display = "none";
            return;
        }
        // readonly
        const readonlyRow = form.querySelector(".field-language_code");
        if (readonlyRow) readonlyRow.style.display = "none";
    }

    // Hide language code on existing field
    forms.forEach(hideLangCodeField);
    const emptyForm = fieldset.querySelector(".inline-related.dynamic-translations.empty-form");
    if (emptyForm) hideLangCodeField(emptyForm);

    // Hide the add-row Django natif
    const djangoAddRow = fieldset.querySelector(".add-row");
    if (djangoAddRow) djangoAddRow.style.display = "none";

    const tabs = document.createElement("div");
    tabs.className = "translation-tabs";

    const originalAddLink = fieldset.querySelector(".add-row a");

    function switchToLang(lang, buttonEl) {
        fieldset.querySelectorAll(".inline-related.dynamic-translations:not(.empty-form)").forEach(f => {
            f.style.display = "none";
        });

        fieldset.querySelectorAll(".translation-add-row").forEach(el => el.remove());
        tabs.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        buttonEl.classList.add("active");

        if (langForms[lang]) {
            langForms[lang].style.display = "block";
        } else {
            // No existing translation — display add button only if add-row is available
            if (originalAddLink) {
                const addRow = document.createElement("div");
                addRow.className = "translation-add-row";
                addRow.innerHTML = `<a href="#">➕ Ajouter la traduction "${lang.toUpperCase()}"</a>`;

                addRow.querySelector("a").addEventListener("click", function (e) {
                    e.preventDefault();

                    const observer = new MutationObserver((mutations) => {
                        for (const mutation of mutations) {
                            for (const node of mutation.addedNodes) {
                                if (
                                    node.nodeType === Node.ELEMENT_NODE &&
                                    node.classList.contains("dynamic-translations") &&
                                    !node.classList.contains("empty-form")
                                ) {
                                    observer.disconnect();

                                    const input = node.querySelector("input[name$='language_code']");
                                    if (input) {
                                        input.value = lang;
                                        hideLangCodeField(node);
                                    }

                                    langForms[lang] = node;
                                    addRow.remove();
                                    node.style.display = "block";
                                    buttonEl.classList.remove("missing");

                                    return;
                                }
                            }
                        }
                    });

                    observer.observe(fieldset, { childList: true, subtree: true });
                    originalAddLink.click();
                });

                fieldset.appendChild(addRow);
            } else {
                // Readonly : No button
                const addRow = document.createElement("div");
                addRow.className = "translation-add-row translation-missing-notice";
                addRow.textContent = `Aucune traduction disponible pour "${lang.toUpperCase()}".`;
                fieldset.appendChild(addRow);
            }
        }
    }

    languages.forEach((lang) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = lang.toUpperCase();

        if (!langForms[lang]) button.classList.add("missing");

        button.addEventListener("click", () => switchToLang(lang, button));
        tabs.appendChild(button);
    });

    fieldset.insertBefore(tabs, fieldset.firstChild);

    const firstButton = tabs.querySelector("button");
    switchToLang(languages[0], firstButton);
});
