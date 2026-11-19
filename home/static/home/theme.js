(() => {
    const buttons = document.querySelectorAll("[data-theme-toggle]");
    const choices = document.querySelectorAll("[data-theme-set]");

    function updateButtons(theme) {
        const nextTheme = theme === "dark" ? "light" : "dark";
        buttons.forEach((button) => {
            button.setAttribute("aria-label", `Ativar tema ${nextTheme === "light" ? "claro" : "escuro"}`);
        });
        choices.forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.themeSet === theme));
        });
    }

    let currentTheme = document.documentElement.dataset.theme;
    updateButtons(currentTheme);

    function setTheme(theme) {
        currentTheme = theme;
        document.documentElement.dataset.theme = theme;
        try {
            localStorage.setItem("partyboxd-theme", theme);
        } catch (_) {}
        updateButtons(theme);
    }

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            setTheme(currentTheme === "dark" ? "light" : "dark");
        });
    });
    choices.forEach((button) => {
        button.addEventListener("click", () => setTheme(button.dataset.themeSet));
    });

})();
