import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.cincosas.com',
        pathname: '/2mp21d4s/photos/**',
      },
      {
        protocol: 'https',
        hostname: 'cinco.net.co',
        pathname: '/perfil/photos/**',
      },
    ],
    // Configuración de caché para imágenes externas
    minimumCacheTTL: 31536000, // 1 año en segundos
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  webpack(config) {
    config.module.rules.push({
      test: /\.svg$/,
      use: ["@svgr/webpack"],
    });
    return config;
  },
    
    turbopack: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  
};

export default nextConfig;
