window.addEventListener("load", function () {
    const fieldset = document.querySelector(".inline-group");
    if (!fieldset) return;

    const languages = window.AVAILABLE_LANGUAGES || [];
    if (!languages.length) return;

    const forms = Array.from(
        fieldset.querySelectorAll(".inline-related.dynamic-translations:not(.empty-form)")
    );

    // Map language → form existant
    const langForms = {};
    forms.forEach(f => {
        const input = f.querySelector("input[name$='language_code']");
        if (input) langForms[input.value] = f;
    });

    // Hide the language_code field on all existing forms
    forms.forEach(f => {
        const input = f.querySelector("input[name$='language_code']");
        if (!input) return;
        const row = input.closest(".form-row") || input.closest("p") || input.parentElement;
        if (row) row.style.display = "none";
    });

    // Hide and prepare the empty form (template for adding)
    const emptyForm = fieldset.querySelector(".inline-related.dynamic-translations.empty-form");
    if (emptyForm) {
        const emptyInput = emptyForm.querySelector("input[name$='language_code']");
        if (emptyInput) {
            const row = emptyInput.closest(".form-row") || emptyInput.closest("p") || emptyInput.parentElement;
            if (row) row.style.display = "none";
        }
    }

    // create the tabs
    const tabs = document.createElement("div");
    tabs.className = "translation-tabs";

    // “Add” button per tab (cloned from Django's add-row)
    const originalAddLink = fieldset.querySelector(".add-row a");

    function switchToLang(lang, buttonEl) {
        // hide all the forms
        forms.forEach(f => (f.style.display = "none"));

        // Hide all the add-rows injected
        fieldset.querySelectorAll(".translation-add-row").forEach(el => el.remove());

        tabs.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        buttonEl.classList.add("active");

        if (langForms[lang]) {
            // Existing translation: display the form
            langForms[lang].style.display = "block";
        } else {
            // No translation: display a context-sensitive add button
            if (originalAddLink) {
                const addRow = document.createElement("div");
                addRow.className = "translation-add-row";
                addRow.innerHTML = `<a href="#">➕ Ajouter la traduction "${lang.toUpperCase()}"</a>`;
                addRow.querySelector("a").addEventListener("click", function (e) {
                    e.preventDefault();
                    // Simulate clicking on the real Django link to clone the empty form
                    originalAddLink.click();

                    // After the click, Django adds a new form: we assign it the language_code.
                    setTimeout(() => {
                        const newForms = Array.from(
                            fieldset.querySelectorAll(".inline-related.dynamic-translations:not(.empty-form)")
                        );
                        const newForm = newForms[newForms.length - 1];
                        if (!newForm) return;

                        const input = newForm.querySelector("input[name$='language_code']");
                        if (input) {
                            input.value = lang;
                            const row = input.closest(".form-row") || input.closest("p") || input.parentElement;
                            if (row) row.style.display = "none";
                        }

                        // hide the add row
                        const djangoAddRow = fieldset.querySelector(".add-row");
                        if (djangoAddRow) djangoAddRow.style.display = "none";

                        // Reference the form in langForms
                        langForms[lang] = newForm;

                        // Remove the context menu add button
                        addRow.remove();

                        // show new form
                        newForm.style.display = "block";
                    }, 50);
                });

                fieldset.appendChild(addRow);
            }
        }
    }

    languages.forEach((lang, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = lang.toUpperCase();
        button.addEventListener("click", () => switchToLang(lang, button));
        tabs.appendChild(button);
    });

    fieldset.insertBefore(tabs, fieldset.firstChild);

    // hide the add-row Django
    const djangoAddRow = fieldset.querySelector(".add-row");
    if (djangoAddRow) djangoAddRow.style.display = "none";

    // show first tab
    const firstButton = tabs.querySelector("button");
    switchToLang(languages[0], firstButton);
});
