from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

import numpy as np
import pyarrow as pa
from numpy.lib.arraysetops import isin

from ..utils.streaming_download_manager import xopen


if TYPE_CHECKING:
    import PIL.Image


class _ImageExtensionType(pa.PyExtensionType):
    def __init__(self, storage_dtype: str):
        self.storage_dtype = storage_dtype
        if storage_dtype == "string":
            pa_storage_dtype = pa.string()
        elif storage_dtype == "bytes":
            pa_storage_dtype = pa.binary()
        else:
            pa_storage_dtype = pa.struct({"path": pa.string(), "bytes": pa.binary()})
        pa.PyExtensionType.__init__(self, pa_storage_dtype)

    def __reduce__(self):
        return self.__class__, (self.storage_dtype,)


@dataclass(unsafe_hash=True)
class Image:
    """Image feature to read image data from an image file.

    Input: The Image feature accepts as input:
    - A :obj:`str`: Absolute path to the image file (i.e. random access is allowed).
    - A :obj:`dict` with the keys:

        - path: String with relative path of the image file to the archive file.
        - bytes: Bytes of the image file.

      This is useful for archived files with sequential access.
    """

    _storage_dtype: str = "string"
    id: Optional[str] = None
    # Automatically constructed
    dtype: ClassVar[str] = "dict"
    pa_type: ClassVar[Any] = None
    _type: str = field(default="Image", init=False, repr=False)

    def __call__(self):
        return _ImageExtensionType(self._storage_dtype)

    def encode_example(self, value):
        """Encode example into a format for Arrow.

        Args:
            value (:obj:`str`, :obj:`bytes` or :obj:`dict`): Data passed as input to Image feature.

        Returns:
            :obj:`str` or :obj:`dict`
        """
        # TODO(mariosasko): implement np.ndarray encoding
        if isinstance(value, (bytes, np.ndarray)):
            self._storage_dtype = "bytes"
        elif isinstance(value, dict):
            self._storage_dtype = "struct"
        return value

    def decode_example(self, value):
        """Decode example image file into image data.

        Args:
            value (obj:`str` or :obj:`dict`): a string with the absolute image file path, image bytes or a dictionary with
                keys:
                - path: String with absolute or relative audio file path.
                - bytes: Optionally, the bytes of the audio file.

        Returns:
            :obj:`PIL.Image.Image`
        """
        try:
            import PIL.Image
        except ImportError as err:
            raise ImportError("To support decoding images, please install 'Pillow'.") from err

        if isinstance(value, str):
            with xopen(value, "rb") as f:
                image = PIL.Image.open(f)
        elif isinstance(value, bytes):
            image = PIL.Image.open(BytesIO(value))
        elif isinstance(value, dict):
            image = PIL.Image.open(BytesIO(value["bytes"]))
        return image


def image_to_bytes(image: "PIL.Image.Image") -> bytes:
    """Convert a PIL Image object to bytes using lossless PNG compression."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def encode_list_of_images(images: List["PIL.Image.Image"]) -> List[bytes]:
    """Encode the list of PIL Image objects into a list of bytes."""
    return [image_to_bytes(image) for image in images]