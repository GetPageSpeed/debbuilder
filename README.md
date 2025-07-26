https://chatgpt.com/c/66eeef52-90fc-8011-8554-a025ed2c2438

```bash
./crypt-keeper.sh generate ubuntu noble
docker build --tag debbuilder:ubuntu-noble ubuntu/noble
docker run -v $(pwd)/minimal-package:/sources -v $(pwd)/output:/output my-deb-builder-image ./build-deb.sh

```
