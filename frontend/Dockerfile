FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine

# Remove default nginx config and pages
RUN rm -f /etc/nginx/conf.d/default.conf && \
    rm -rf /usr/share/nginx/html && \
    mkdir -p /usr/share/nginx/html

# Copy custom nginx config
COPY deploy/nginx.conf /etc/nginx/nginx.conf

# Copy built frontend
COPY --from=build /app/dist /usr/share/nginx/html

# Custom error pages that don't leak server info
RUN printf '<!DOCTYPE html><html><head><title>Not Found</title></head><body><h1>Not Found</h1></body></html>\n' > /usr/share/nginx/html/404.html && \
    printf '<!DOCTYPE html><html><head><title>Error</title></head><body><h1>Something went wrong</h1></body></html>\n' > /usr/share/nginx/html/50x.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
