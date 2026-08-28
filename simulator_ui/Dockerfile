FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_SIMULATOR_API_URL
ENV VITE_SIMULATOR_API_URL=$VITE_SIMULATOR_API_URL
COPY package.json .
RUN npm install
COPY . .
RUN test -n "$VITE_SIMULATOR_API_URL" || (echo "VITE_SIMULATOR_API_URL is required" && exit 1)
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
