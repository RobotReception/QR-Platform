const axios = require('axios');
console.log(axios.getUri({ baseURL: 'http://localhost:8030/api/v1', url: '/auth/password-reset/send-otp' }));
