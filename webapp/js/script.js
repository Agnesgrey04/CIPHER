
const { createApp } = Vue;

createApp({
    data() {
        return {
            role: "Client",
            username: "",
            password: "",
            showPassword: false,
            error: "",
            loading: false
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
                this.error = "Please enter both email and password.";
                return;
            }

            this.error = "";
            this.loading = true;

            try {
                const response = await fetch(
                    "http://127.0.0.1:8000/auth/login",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            email: this.username.trim(),
                            password: this.password
                        })
                    }
                );

                const data = await response.json();

                if (!response.ok) {
                    this.error = data.detail || "Invalid email or password.";
                    return;
                }

                if (!data.access_token) {
                    this.error = "The server did not return an access token.";
                    return;
                }

                // Check whether the authenticated account has the selected role
                if (
                    data.role.toLowerCase() !== this.role.toLowerCase()
                ) {
                    this.error = "You do not have permission to access this login.";
                    return;
                }

                sessionStorage.setItem("cipherToken", data.access_token);
                sessionStorage.setItem("cipherRole", data.role);
                sessionStorage.setItem("cipherEmail", data.email);

                window.location.href = "camera.html";

            } catch (err) {
                this.error =
                    "Cannot connect to the CIPHER server. Please try again.";

                console.error("CIPHER login error:", err);

            } finally {
                this.loading = false;
            }
        }
    }
}).mount("#app");
