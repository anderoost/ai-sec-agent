import sys
print('PY', sys.version)
try:
    import transformers
    print('TRANSFORMERS', transformers.__version__)
except Exception as e:
    print('TRANSFORMERS_IMPORT_ERROR', repr(e))
try:
    import torch
    print('TORCH', torch.__version__)
except Exception as e:
    print('TORCH_IMPORT_ERROR', repr(e))
