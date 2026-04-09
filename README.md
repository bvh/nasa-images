# NASA Images

A simple Python script for working with the NASA images API.

## Usage

### Fetching Images and Metadata

The `fetch` operation looks up the image asset and tries to download the image
(original size/file) and metadata. There are several ways to indicate the image
or images that you'd like to download.

To download a single image by NASA ID:
```
uv run nasa.py fetch --id art002e000192
```

To download a single image based on a filename:
```
uv run nasa.py fetch --image images/art002e000192~thumb.jpg
```

To download one or more images based on a file containing a list of NASA ID's:
```
uv run nasa.py fetch --list image_ids.txt
```

To download one or more images based on images in a directory:
```
uv run nasa.py fetch --dir images/
```

Note that in all cases, it will download the **original** images (not any of
the other sizes) and the metadata JSON file (renamed to match the NASA ID).
There is currently no way to specific other image sies to download, or to avoid
downloading the metadata file.


## Reference

- [NASA Image and Video Library](https://images.nasa.gov/)
    - [API Documentation](https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf) (PDF)
    - [Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)
