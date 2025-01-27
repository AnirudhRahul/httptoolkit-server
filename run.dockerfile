# -------------------------------------------------------
# Sample Dockerfile for running an Android emulator, ADB,
# Playwright, and your run_all_in_python.py script
# -------------------------------------------------------
FROM ubuntu:22.04

# Suppress interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set up environment variables for Android
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=$PATH:$ANDROID_SDK_ROOT/emulator:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin

# Install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    libglu-dev \
    libpulse0 \
    libasound2 \
    libncurses5 \
    libstdc++6 \
    openjdk-11-jdk \
    python3 \
    python3-pip \
    nodejs \
    npm \
    lsof \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------
# Install Android command-line tools
# -------------------------------------------------------
WORKDIR /opt
RUN wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O cmdline-tools.zip \
    && mkdir -p android-sdk/cmdline-tools \
    && unzip cmdline-tools.zip -d android-sdk/cmdline-tools \
    && mv android-sdk/cmdline-tools/cmdline-tools android-sdk/cmdline-tools/latest \
    && rm cmdline-tools.zip

# Accept all licenses (by piping "yes")
RUN yes | sdkmanager --sdk_root=${ANDROID_SDK_ROOT} --licenses

# -------------------------------------------------------
# Install required SDK components:
#  - Platform Tools
#  - Emulator
#  - Platform + Build Tools
#  - System images (adjust to your needs)
# -------------------------------------------------------
RUN sdkmanager --sdk_root=${ANDROID_SDK_ROOT} --install \
    "platform-tools" \
    "emulator" \
    "platforms;android-31" \
    "build-tools;31.0.0" \
    "system-images;android-31;google_apis;arm64-v8a"

# -------------------------------------------------------
# Create and accept a new AVD
# (Adjust name to match your script references.)
# -------------------------------------------------------
RUN yes "no" | avdmanager create avd \
    --name Pixel_XL_API_31-v2 \
    --package "system-images;android-31;google_apis;arm64-v8a" \
    --device "pixel_xl" \
    --tag "google_apis"

# -------------------------------------------------------
# Install Python dependencies:
#  1) playwright and its browsers
#  2) any other libs from requirements.txt (if you have one)
# -------------------------------------------------------
RUN pip3 install --no-cache-dir playwright \
    && playwright install --with-deps chromium

# Copy your script and supporting files into /app
WORKDIR /app

# (Adjust paths as needed. If you have additional dependencies
#  or a custom requirements.txt, copy and install them.)
COPY run_all_in_python.py /app/run_all_in_python.py

# Copy the TikTok APK
COPY tiktok-v30.1.2.apk /app/tiktok-v30.1.2.apk

# If you need your custom root scripts and images:
# COPY rootAVD.sh /app/rootAVD.sh
# COPY ramdisk.img /app/ramdisk.img
# Make them executable
# RUN chmod +x /app/rootAVD.sh

# Example: If you have additional Python dependencies, do:
# COPY requirements.txt /app/requirements.txt
# RUN pip3 install --no-cache-dir -r requirements.txt

# -------------------------------------------------------
# Expose ports if needed for HTTP Toolkit or any local server
# (By default, your code uses HTTP Toolkit's remote URL, so not strictly required.)
# -------------------------------------------------------
EXPOSE 8080

# -------------------------------------------------------
# Final command
# The script requires a TTY in many cases, or you might want
# to `docker exec` into the container and run it manually.
# We'll set it as an entrypoint for convenience.
# -------------------------------------------------------
ENTRYPOINT ["python3", "/app/run_all_in_python.py"]