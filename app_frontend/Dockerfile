# Stage 1 — build Flutter web
FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app

# Fetch dependencies first so this layer is cached unless pubspec changes
COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get

# Copy source
COPY . .

# Build-time config injected via --dart-define
ARG BACKEND_URL=http://localhost:8000
ARG WS_URL=ws://localhost:8000/ws
ARG DEFAULT_DISTRICT=mangaluru
ARG DEFAULT_LANGUAGE=kn

RUN flutter config --enable-web && \
    flutter build web --release \
      --dart-define=BACKEND_URL=${BACKEND_URL} \
      --dart-define=WS_URL=${WS_URL} \
      --dart-define=DEFAULT_DISTRICT=${DEFAULT_DISTRICT} \
      --dart-define=DEFAULT_LANGUAGE=${DEFAULT_LANGUAGE}

# Stage 2 — serve with nginx
FROM nginx:alpine

COPY --from=build /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
