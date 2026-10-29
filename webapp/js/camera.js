
const { createApp } = Vue;

// The backend is running locally on port 8000.
// The actual WebSocket endpoint was identified in backend/stream.html.
const CAMERA_WS_URL = "ws://127.0.0.1:8000/ws/video";

createApp({
    data() {
        return {
            activeNav: "Cameras",
            selectedId: "CAM-01",

            currentDate: "",
            currentTime: "",

            connectionState: "disconnected",
            statusMessage: "Waiting to connect to the camera server.",

            cameraSocket: null,
            reconnectTimeout: null,
            clockInterval: null,
            reconnectAttempts: 0,
            shouldReconnect: true,

            frameUrl: "",
            hasFrame: false,

            navigation: [
                { label: "Cameras", icon: "▣" },
                { label: "Overview", icon: "⌂" },
                { label: "Events", icon: "⚑" },
                { label: "Evidence", icon: "◇" },
                { label: "Support", icon: "ⓘ" },
                { label: "System Settings", icon: "⚙" }
            ],

            cameras: [
                { id: "CAM-01", name: "Main Entrance" },
                { id: "CAM-02", name: "North Corridor" },
                { id: "CAM-03", name: "Parking Area" },
                { id: "CAM-04", name: "Rear Entrance" },
                { id: "CAM-05", name: "Main Hall" },
                { id: "CAM-06", name: "Side Gate" },
                { id: "CAM-07", name: "East Wing" }
            ]
        };
    },

    computed: {
        selectedCamera() {
            return this.cameras.find(
                camera => camera.id === this.selectedId
            ) || this.cameras[0];
        },

        connectionLabel() {
            const labels = {
                connected: "Connected",
                connecting: "Connecting",
                disconnected: "Disconnected",
                error: "Connection error"
            };

            return labels[this.connectionState] || "Unknown";
        }
    },

    methods: {
        updateClock() {
            const now = new Date();

            this.currentDate = new Intl.DateTimeFormat("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }).format(now);

            this.currentTime = new Intl.DateTimeFormat("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false
            }).format(now);
        },

        selectCamera(camera) {
            this.selectedId = camera.id;

            // The current backend WebSocket supplies one stream.
            // Changing the selected label does not switch the physical camera.
        },

        previousCamera() {
            const currentIndex = this.cameras.findIndex(
                camera => camera.id === this.selectedId
            );

            const previousIndex =
                (currentIndex - 1 + this.cameras.length) %
                this.cameras.length;

            this.selectedId = this.cameras[previousIndex].id;
        },

        navigate(item) {
            this.activeNav = item.label;

            if (item.label === "Cameras") {
                return;
            }

            alert(item.label + " page will be implemented next.");
        },

        logout() {
            this.shouldReconnect = false;

            if (this.cameraSocket) {
                this.cameraSocket.close();
            }

            window.location.href = "index.html";
        },

        connectCamera() {
            // Avoid opening multiple simultaneous WebSocket connections.
            if (
                this.cameraSocket &&
                (
                    this.cameraSocket.readyState === WebSocket.CONNECTING ||
                    this.cameraSocket.readyState === WebSocket.OPEN
                )
            ) {
                return;
            }

            this.shouldReconnect = true;
            this.connectionState = "connecting";
            this.statusMessage = "Connecting to the CIPHER camera server...";

            if (this.reconnectTimeout) {
                clearTimeout(this.reconnectTimeout);
                this.reconnectTimeout = null;
            }

            let socket;

            try {
                socket = new WebSocket(CAMERA_WS_URL);
                socket.binaryType = "blob";
                this.cameraSocket = socket;
            } catch (error) {
                console.error("Unable to create camera WebSocket:", error);
                this.connectionState = "error";
                this.statusMessage = "Could not create the camera connection.";
                this.scheduleReconnect();
                return;
            }

            socket.onopen = () => {
                if (this.cameraSocket !== socket) return;

                console.log("Connected to CIPHER video stream.");

                this.connectionState = "connected";
                this.statusMessage = "Connected. Waiting for the first video frame...";
                this.reconnectAttempts = 0;
            };

            socket.onmessage = (event) => {
                if (this.cameraSocket !== socket) return;

                // The supplied stream.html indicates that the server sends
                // individual JPEG frames over the WebSocket.
                let blob;

                if (event.data instanceof Blob) {
                    blob = event.data;
                } else if (event.data instanceof ArrayBuffer) {
                    blob = new Blob(
                        [event.data],
                        { type: "image/jpeg" }
                    );
                } else {
                    console.warn(
                        "Received a non-binary camera message:",
                        event.data
                    );
                    return;
                }

                if (this.frameUrl) {
                    URL.revokeObjectURL(this.frameUrl);
                }

                this.frameUrl = URL.createObjectURL(blob);
                this.hasFrame = true;
                this.statusMessage = "Receiving live camera frames.";
            };

            socket.onerror = (error) => {
                if (this.cameraSocket !== socket) return;

                console.error("CIPHER camera WebSocket error:", error);
                this.connectionState = "error";
                this.statusMessage =
                    "Unable to connect. Check that the camera stream is running.";
            };

            socket.onclose = () => {
                if (this.cameraSocket !== socket) return;

                this.cameraSocket = null;

                if (this.shouldReconnect) {
                    this.connectionState = "disconnected";
                    this.statusMessage =
                        "Stream disconnected. Attempting to reconnect...";
                    this.scheduleReconnect();
                }
            };
        },

        scheduleReconnect() {
            if (!this.shouldReconnect || this.reconnectTimeout) return;

            this.reconnectAttempts += 1;

            const delay = Math.min(
                1000 * Math.pow(2, this.reconnectAttempts - 1),
                10000
            );

            this.reconnectTimeout = window.setTimeout(() => {
                this.reconnectTimeout = null;

                if (this.shouldReconnect) {
                    this.connectCamera();
                }
            }, delay);
        }
    },

    mounted() {
        this.updateClock();

        this.clockInterval = window.setInterval(
            this.updateClock,
            1000
        );

        this.connectCamera();
    },

    beforeUnmount() {
        this.shouldReconnect = false;

        if (this.clockInterval) {
            clearInterval(this.clockInterval);
        }

        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
        }

        if (this.cameraSocket) {
            const socket = this.cameraSocket;
            this.cameraSocket = null;
            socket.close();
        }

        if (this.frameUrl) {
            URL.revokeObjectURL(this.frameUrl);
            this.frameUrl = "";
        }
    }
}).mount("#cameraApp");
