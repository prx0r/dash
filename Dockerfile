FROM node:22-alpine
WORKDIR /app
COPY . .
ENV NODE_ENV=production PORT=8787 HOST=0.0.0.0
RUN node scripts/build-machine-files.mjs && node scripts/validate.mjs
EXPOSE 8787
CMD ["node","server.mjs"]
