FROM node:18-bookworm-slim AS build
COPY web-panel/package*.json .
RUN npm ci
COPY web-panel/* ./
RUN npm run build

# FROM node:18-bookworm-slim
# USER node
# WORKDIR /home/node/app
# COPY --from=build --chown=node:node web-panel/package*.json .
# RUN npm ci --omit=dev
# COPY --from=build --chown=node:node web-panel/dist/* .

FROM python:3.11.5-slim-bookworm
RUN pip3 install pipenv
WORKDIR /app
COPY tracker/Pipfile* ./
RUN pipenv install
COPY --from=build --chown=node:node web-panel/dist ./static
COPY tracker .

CMD [ "pipenv", "run" , "uvicorn", "server:app", "--workers", "4"]
