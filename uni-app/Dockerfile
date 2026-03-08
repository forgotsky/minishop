FROM node:18-bullseye-slim as build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build:h5

FROM nginx:1.25-alpine
COPY --from=build /app/dist/build/h5 /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
