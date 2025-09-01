# Redis Configuration for Regulation Scraping System
FROM redis:7-alpine

# Set working directory
WORKDIR /usr/local/etc/redis

# Copy custom Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Create directory for Redis data
RUN mkdir -p /data

# Install additional tools for monitoring
RUN apk add --no-cache \
    bash \
    curl \
    procps

# Expose Redis port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD redis-cli ping || exit 1

# Set proper permissions
RUN chown -R redis:redis /data /usr/local/etc/redis

# Switch to redis user
USER redis

# Start Redis with custom configuration
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]