# Stage 1: Build the React app
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config (as template for envsubst)
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Cloud Run uses port 8080
EXPOSE 8080

# nginx docker image supports envsubst on templates automatically
# BACKEND_URL will be substituted at container start
CMD ["nginx", "-g", "daemon off;"]
