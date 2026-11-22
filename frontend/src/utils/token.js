export const saveToken = (token) => {
  localStorage.setItem("access_token", token);
};

export const getToken = () => {
  return localStorage.getItem("access_token");
};

export const removeToken = () => {
  localStorage.removeItem("access_token");
};

export const saveRefreshToken = (token) => {
  localStorage.setItem("refresh_token", token);
};

export const getRefreshToken = () => {
  return localStorage.getItem("refresh_token");
};

export const removeRefreshToken = () => {
  localStorage.removeItem("refresh_token");
};

export const clearTokens = () => {
  removeToken();
  removeRefreshToken();
};
