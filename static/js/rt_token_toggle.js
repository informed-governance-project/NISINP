document.addEventListener("DOMContentLoaded", function () {
    const tokenInput = document.getElementById("id_rt_token");
    if (!tokenInput) return;

    if (document.getElementById("rt-token-toggle")) return;

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.id = "rt-token-toggle";
    toggleBtn.className = "button";
    toggleBtn.textContent = gettext("Show");
    toggleBtn.style.marginLeft = "10px";
    toggleBtn.style.fontSize = "0.8em";
    toggleBtn.style.padding = "2px 6px";

    tokenInput.parentNode.insertBefore(toggleBtn, tokenInput.nextSibling);

    toggleBtn.addEventListener("click", function () {
        const isHidden = tokenInput.type === "password";
        tokenInput.type = isHidden ? "text" : "password";
        toggleBtn.textContent = isHidden ? gettext("Hide") : gettext("Show");
    });
});
