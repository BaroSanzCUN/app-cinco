module.exports = {
  apps: [
    {
      name: "app-cinco-frontend",
      script: "npm",
      args: "start",
      cwd: "/home/admcinco/app_cinco/frontend",
      env: {
        NODE_ENV: "production",
        PORT: 3000,
      },
      env_development: {
        NODE_ENV: "development",
      },
    },
  ],
};
