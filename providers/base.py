# providers/base.py

class AIProvider:
    name = "base"

    def get_extensions(self, url, headers, max_extensions):
        raise NotImplementedError
