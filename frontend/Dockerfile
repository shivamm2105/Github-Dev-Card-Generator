FROM nginx:alpine

# Copy index.html to a template directory
COPY index.html /etc/nginx/templates/index.html.template

# Default backend URL (can be overridden by environment variable)
ENV BACKEND_URL=http://localhost:8080

# Use a custom entrypoint to replace the backend URL at runtime
# envsubst will replace $BACKEND_URL in the template and write to the final html location
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /etc/nginx/templates/index.html.template > /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]

EXPOSE 80
