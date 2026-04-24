# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_ENGINE_URL=http://localhost:8080
ENV VITE_ENGINE_URL=$VITE_ENGINE_URL
RUN npm run build

# Runtime stage — locked deps, non-root user
FROM node:20-alpine
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json /app/package-lock.json ./
RUN npm ci --omit=dev
USER appuser
EXPOSE 3000
ENV PORT=3000
CMD ["node", "build"]
