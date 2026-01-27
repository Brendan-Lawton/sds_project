# SDS Project

## Prerequisites
* Python 3.10

## Setup Instructions
1. Create `.venv` folder
    ```bash
    python3.10 -m venv .venv
    ```

2. Source `.venv` folder
    ```bash
    source .venv/activate/bin
    ```

3. Install requirements
    ```bash
    pip install -r requirements.txt
    ```

4. Add the `asr_server.py` file to the root folder.
5. Add the `web/` folder to the root folder
6  Delete following files before you can retrain with `rasa train`
    - data/._nlu.yml
    - data/._rules.yml
    - data/._stories.yml

## Running the Application
Use the start script
```bash
./start_service.sh
```
The application will be accessible at `http://localhost:8080/web/`.

Alternatively, you can run the application directly using the following commands in separate terminal windows:
```bash
rasa run --enable-api --connector rest --cors "*" --port 5005
```
```bash
rasa run actions
```
```bash
python asr_server.py
```
```bash
python -m http.server 8080
```

## Usage
Train the Rasa model:
```bash
rasa train
```

Start the Rasa cli:
```bash
rasa shell
```
