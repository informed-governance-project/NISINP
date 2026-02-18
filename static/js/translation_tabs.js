window.addEventListener("load", function () {
    const fieldset = document.querySelector(".inline-group");
    if (!fieldset) return;

    const languages = window.AVAILABLE_LANGUAGES || [];
    if (!languages.length) return;

    // On récupère toutes les forms dynamiques (existantes)
    const forms = Array.from(fieldset.querySelectorAll(".inline-related.dynamic-translations:not(.empty-form)"));

    // Création de l'objet langue → form
    const langForms = {};
    languages.forEach(lang => {
        langForms[lang] = forms.find(f => f.querySelector("input[name$='language_code']").value === lang);
    });

    // Si une langue n’a pas de form existante, on laisse null → l'utilisateur pourra l'ajouter
    const tabs = document.createElement("div");
    tabs.className = "translation-tabs";

    languages.forEach((lang, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = lang.toUpperCase();

        button.addEventListener("click", function () {
            forms.forEach(f => f.style.display = "none");
            if (langForms[lang]) langForms[lang].style.display = "block";

            tabs.querySelectorAll("button").forEach(b => b.classList.remove("active"));
            button.classList.add("active");
        });

        tabs.appendChild(button);
    });

    // Insert tabs en haut du fieldset
    fieldset.insertBefore(tabs, fieldset.firstChild);

    // Affiche la première langue
    const firstLang = languages[0];
    if (langForms[firstLang]) langForms[firstLang].style.display = "block";
    tabs.querySelector("button").classList.add("active");

    // Cache les autres
    languages.slice(1).forEach(lang => {
        if (langForms[lang]) langForms[lang].style.display = "none";
    });
});
