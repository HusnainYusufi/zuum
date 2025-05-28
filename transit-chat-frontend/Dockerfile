# Use Node.js for development server
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Expose port 3000 (React dev server default)
EXPOSE 3000

# Start the development server
CMD ["pnpm", "start"] 