/**
 * Simple 1D Kalman Filter
 *
 * @param {object} options
 * @param {number} [options.R=1]   Process noise covariance
 * @param {number} [options.Q=1]   Measurement noise covariance
 * @param {number} [options.A=1]   State transition matrix (usually 1 for position)
 * @param {number} [options.B=0]   Control matrix (optional, assumes no control input)
 * @param {number} [options.C=1]   Measurement matrix (usually 1)
 * @param {number} [options.initialEstimate] Initial state estimate
 * @param {number} [options.initialCovariance=1] Initial estimate covariance
 */
class KalmanFilter {
    constructor(options = {}) {
        this.R = options.R === undefined ? 1 : options.R;         // Process noise covariance
        this.Q = options.Q === undefined ? 1 : options.Q;         // Measurement noise covariance
        this.A = options.A === undefined ? 1 : options.A;         // State transition matrix
        this.B = options.B === undefined ? 0 : options.B;         // Control matrix
        this.C = options.C === undefined ? 1 : options.C;         // Measurement matrix

        this.x = options.initialEstimate === undefined ? 0 : options.initialEstimate; // Initial state estimate
        this.P = options.initialCovariance === undefined ? 1 : options.initialCovariance; // Initial estimate covariance
    }

    /**
     * Filter a measurement
     * @param {number} z Measurement value
     * @param {number} [u=0] Control input (optional)
     * @returns {number} Filtered value
     */
    update(z, u = 0) {
        // Prediction
        const x_pred = this.A * this.x + this.B * u;
        const P_pred = this.A * this.P * this.A + this.R;

        // Update
        const K = (P_pred * this.C) / (this.C * P_pred * this.C + this.Q);
        this.x = x_pred + K * (z - this.C * x_pred);
        this.P = (1 - K * this.C) * P_pred;

        return this.x;
    }

    /**
     * Get the current state estimate
     * @returns {number} Current state estimate
     */
    getState() {
        return this.x;
    }

    /**
     * Reset the filter to initial conditions or new ones
     * @param {number} initialEstimate New initial estimate
     * @param {number} [initialCovariance=1] New initial covariance
     */
    reset(initialEstimate, initialCovariance = 1) {
         this.x = initialEstimate === undefined ? 0 : initialEstimate;
         this.P = initialCovariance === undefined ? 1 : initialCovariance;
    }
}

export default KalmanFilter; 