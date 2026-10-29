
const { createApp } = Vue;

createApp({
    data() {
        return {
            role: "Client",
            username: "",
            password: "",
            showPassword: false,
            error: ""
        };
    },

    computed: {
        otherRole() {
            return this.role === "Client" ? "Admin" : "Client";
        }
    },

    methods: {
        toggleRole() {
            this.role = this.otherRole;
            this.error = "";
        },

        async handleLogin() {
            if (!this.username.trim() || !this.password) {
                this.error = "Please enter both username and password.";
                return;
            }

            this.error = "";

            try {
                const response = await fetch(
                    "https://127.0.0.1:8000/auth/login",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            username: this.username.trim(),
                            password: this.password,
                            role: this.role.toLowerCase()
                        })
                    }
                );

                const data = await response.json();

                if (!response.ok) {
                    this.error =
                        data.detail || "Invalid username or password.";
                    return;
                }

                if (!data.access_token) {
                    this.error = "The server did not return an access token.";
                    return;
                }

                sessionStorage.setItem(
                    "cipherToken",
                    data.access_token
                );

                window.location.href = "camera.html";

            } catch (err) {
                this.error =
                    "Cannot connect to the CIPHER server. Please try again.";

                console.error("CIPHER login error:", err);
            }
        }
    }
}).mount("#app");
