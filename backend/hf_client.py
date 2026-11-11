import base64,json
from openai import OpenAI
from config import HF_TOKEN,HF_MODEL

def analyze_with_huggingface(image_bytes,context):
    client=OpenAI(base_url="https://router.huggingface.co/v1",api_key=HF_TOKEN,timeout=90.0)
    data_url="data:image/jpeg;base64,"+base64.b64encode(image_bytes).decode("ascii")
    system="""You are PlantSense, a cautious plant-health screening assistant. Inspect the image for visible symptoms and use sensor readings as context. Do not claim a definitive diagnosis from one photograph. If uncertain, say so. Return one valid JSON object only with keys: plant_condition (healthy|possible_stress|possible_disease|uncertain), disease, stress_level (none|low|medium|high|uncertain), visible_symptoms (array), possible_causes (array), confidence (0 to 1), recommendation, limitations (array). Confidence is subjective, not calibrated."""
    response=client.chat.completions.create(model=HF_MODEL,messages=[
      {"role":"system","content":system},
      {"role":"user","content":[{"type":"text","text":"Plant species, growth stage and sensor context:\n"+json.dumps(context)},
       {"type":"image_url","image_url":{"url":data_url}}]}],temperature=0.1,max_tokens=700)
    content=response.choices[0].message.content or ""
    if isinstance(content,list): content="".join(p.get("text","") for p in content if isinstance(p,dict))
    content=content.strip()
    if content.startswith("```"): content=content.split("\n",1)[-1].rsplit("```",1)[0].strip()
    try: return json.loads(content)
    except json.JSONDecodeError: return {"plant_condition":"uncertain","raw_model_response":content,"parse_error":"Invalid JSON from model"}
