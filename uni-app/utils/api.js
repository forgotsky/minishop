const DEFAULT_BASE_URL = 'http://localhost:8000';

function getBaseUrl() {
  return uni.getStorageSync('API_BASE_URL') || DEFAULT_BASE_URL;
}

export function setBaseUrl(url) {
  if (url) {
    uni.setStorageSync('API_BASE_URL', url);
  }
}

function request(path, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${getBaseUrl()}${path}`,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(res.data?.detail || 'Request failed'));
        }
      },
      fail: (err) => reject(err)
    });
  });
}

export function fetchSkills() {
  return request('/api/skills');
}

export function generateTemplate(subject) {
  return request('/api/template', 'POST', { subject });
}

export function generatePlan(payload) {
  return request('/api/plan', 'POST', payload);
}
