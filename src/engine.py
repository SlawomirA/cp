import json
from types import SimpleNamespace

import requests

class Engine:
    """
    Engine for loading the models.

    Attributes
    ----------
    repetition_penalty : float
        Applies a penalty to reduce usage of words that have already been used recently,
        making the output of the AI less repetitive.
    temperature : float
        Controls how 'Random' the output is by scaling probabilities without removing options.
        Lower value are more logical, but less creative.
    tfs : int
        Alternative to Top-P, this setting removes the least probable words from consideration
        during text generation, considering second order derivatives.
        Can improve the quality and coherence of the generated text.
    top_a : float
        Alternative to Top-P. Remove all tokens that have softmax probability less than top_a*m^2
        where m is the maximum softmax probability. Set value to 0 to disable its effect.
    top_k : float
        This setting limits the number of possible words to choose from to the top K most likely options,
        removing everything else. Can be used with Top-P. Set value to 0 to disable its effect.
    top_p : float
        Discards unlikely text in the sampling process. Only considers words with the highest cumulative
        probabilities summing up to P. Low values make the text predictable, as uncommon tokens are removed.
        Set value to 1 to disable its effect.
    typical : float
        Selects words randomly from the list of possible words, with each word having an equal chance of being selected.
        This method can produce text that is more diverse but may also be less coherent.
        Set value to 1 to disable its effect.
    min_p : float
        An experimental alternative to Top-P that removes tokens under a certain probability.
        Set value to 0 to disable its effect.
    """

    def __init__(self, path: str = 'engine.json'):
        with open(path, "r") as f:
            x = json.loads(f.read(), object_hook=lambda d: SimpleNamespace(**d))


        self.base_path: str = x.base_path
        self.engine_name: str = x.engine_name
        self.model_name: str = x.model_name

        self.port: int = x.port
        self.base_url: str = f"http://localhost:{self.port}"
        self.internal_endpoint: str = f'{self.base_url}{x.api_generate_url}'

        self.log_name: str = x.log_name
        self.log_path: str = f"./{self.log_name}"
        self.show_log_in_console: bool = x.show_log_in_console

        self.prompt: str = ""

        self.max_context_length: int = x.max_context_length
        self.temperature: float = x.temperature
        self.max_length: int = x.max_length
        self.quiet: bool = x.quiet
        self.repetition_penalty: float = x.repetition_penalty
        self.rep_pen_range: int = x.rep_pen_range
        self.tfs: int = x.tfs
        self.top_a: float = x.top_a
        self.top_k: int = x.top_k
        self.top_p: float = x.top_p
        self.typical: int = x.typical
        self.min_p: float = x.min_p

        self.running: bool = False
        open(self.log_path, 'w').close()



    def log(self, message: str) -> None:
        if self.show_log_in_console:
            print(message)
        with open(self.log_path, "a") as f:
            f.write(message)
            f.write('\n')

    async def check_engine(self):
        self.log('Starting engine')

        response = requests.get(f'{self.base_url}')
        print(response.status_code)
        if response.status_code == 200:
            self.log('Engine started')
            self.running = True

    @staticmethod
    def remove_name_from_text(text):
        # Podziel tekst na części za pomocą znaku dwukropka
        parts = text.split(':', 1)
        # Jeśli dwukropek został znaleziony, zwróć wszystko po nim, w przeciwnym razie zwróć cały tekst
        return parts[1].strip() if len(parts) > 1 else text



    def get_request_parameters(self, text: str, question: str):
        return {
            "max_new_tokens": self.max_context_length,
            "max_context_length": self.max_context_length,
            "temperature": self.temperature,
            "max_length": self.max_length,
            "prompt": self.create_prompt(text, question),
            "quiet": self.quiet,
            "rep_pen": self.repetition_penalty,
            "rep_pen_range": self.rep_pen_range,
            "tfs": self.tfs,
            "typical": self.typical,
            "top_a": self.top_a,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "min_p": self.min_p
        }

    def create_prompt(self, text: str, question: str) -> str:
        warmup_example = "Odpowiedź na pytanie powinna być udzielona w języku polskim."
        system: str = f"Jako pomocny doradca prawny przeanalizuj podany tekst i odpowiedz po polsku na poniższe pytania.\n\nPlik:\n{text}\n{warmup_example}"
        user_prompt: str = question
        return f"[INST]{system}\n\n\n{user_prompt}[/INST]"

    def connection(self, text: str, question: str) -> str:
        parameters = self.get_request_parameters(text, question)
        response = requests.post(self.internal_endpoint, json=parameters)

        data = json.loads(response.text)
        for result in data['results']:
            result['text'] = self.remove_name_from_text(result['text'])
        updated_json_string = json.dumps(data, ensure_ascii=False, indent=2)
        return updated_json_string

if __name__ == '__main__':
    engine: Engine = Engine()

    print(engine.connection())
