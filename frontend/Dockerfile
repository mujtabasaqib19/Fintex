# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve (output used by nginx volume mount)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# This image is not directly exposed — nginx container serves the files
# But can be used standalone for testing
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
