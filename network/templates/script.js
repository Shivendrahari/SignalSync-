document.addEventListener("DOMContentLoaded", () => {
    const loginTab = document.getElementById("login-tab");
    const registerTab = document.getElementById("register-tab");
    const loginPane = document.getElementById("login");
    const registerPane = document.getElementById("register");

    loginTab.addEventListener("click", () => {
        loginPane.classList.add("show", "active");
        registerPane.classList.remove("show", "active");
    });

    registerTab.addEventListener("click", () => {
        registerPane.classList.add("show", "active");
        loginPane.classList.remove("show", "active");
    });

    // Default to login tab
    loginTab.click();
});
