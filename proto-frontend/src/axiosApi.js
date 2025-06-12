import axios from "axios";
import { constants } from "./constants/constants";

// Instance with Authorization
const axiosInstance = axios.create({
    baseURL: 'http://192.168.179.180:8000',
    timeout: 15000, // Increased timeout to 15 seconds
    headers: {
        'Content-Type': 'application/json',
        'accept': 'application/json'
    }
});

// Add an interceptor to dynamically set the Authorization header
axiosInstance.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor for better error handling
axiosInstance.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        // Log the error but still reject the promise
        console.error('Axios error:', error);
        return Promise.reject(error);
    }
);

// Instance without Authorization
const axiosInstanceWithoutAuth = axios.create({
    baseURL: constants.ORANGE_PI_URL,
    timeout: 5000, // Increased timeout to 15 seconds
    headers: {
        'Content-Type': 'application/json',
        'accept': 'application/json'
    }
});

export { axiosInstance, axiosInstanceWithoutAuth };