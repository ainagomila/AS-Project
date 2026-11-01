FROM node:24-alpine
WORKDIR /app
# The image's unprivileged "node" user owns /app and node_modules.
# UID should match the owner of the bind-mounted backend/.certs (the start scripts pass it).
ARG UID=1000
RUN if [ "$UID" != 1000 ]; then sed -i "s/^node:x:1000:/node:x:$UID:/" /etc/passwd && chown -R "$UID" /home/node; fi \
    && chown node:node /app
USER node
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
