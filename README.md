```bash
./crypt-keeper.sh generate ubuntu noble
docker build --tag debbuilder:ubuntu-noble ubuntu/noble
docker run -v $(pwd)/minimal-package:/sources -v $(pwd)/output:/output my-deb-builder-image ./build-deb.sh

```
