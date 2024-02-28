import pandas as pd
from telebot.async_telebot import AsyncTeleBot
from telebot.formatting import format_text, mbold, mstrikethrough

from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate
)
from langchain.prompts import PromptTemplate

from langchain.output_parsers import StructuredOutputParser, ResponseSchema, PydanticOutputParser

from langchain.schema import HumanMessage, SystemMessage

# new feature for states.
from telebot.asyncio_handler_backends import State, StatesGroup
from langchain.pydantic_v1 import BaseModel, Field, validator
import logging


class ExerciseStates(StatesGroup):
    three_forms = State()
    translation = State()

chat = ChatOpenAI(temperature=0)


class SentenceVerifier:
    def __init__(self, sentence):
        self._sentence = sentence

    def word_order_verifier(self):
        pass


class StrongVerbsExercise:
    def __init__(self, sample: pd.DataFrame):
        self._sample = sample
        self._russian = sample['Russian'].item()
        self._english = sample['English'].item()
        self._infinitive = sample['Infinitive'].item()
        self._past = sample['Past'].item()
        self._participle = sample['Participle'].item()
        self._sentence_to_translate = None

    async def description(self):
        return f'Provide three forms of a word "{self._russian}" / "{self._english}".\n' + \
              'If you don\'t know, type /keine_ahnung'

    async def help_with_forms(self):
        return f'Three forms of the word "{self._russian}" / "{self._english}" is:\n\n ' + \
               f'{self._infinitive}\n{self._past}\n{self._participle}'

    async def translation_task(self):
        messages = [
            SystemMessage(
                content="You are a helpful assistant"
            ),
            HumanMessage(
                content=f"Generate a sentence that contains a verb {self._english}"
            ),
        ]
        sentence = await chat.ainvoke(messages)
        self._sentence_to_translate = sentence
        return 'Translate the sentence:\n' + sentence.content

    async def verify_translation(self, translation):
        messages = [
            SystemMessage(
                content="You are a helpful assistant"
            ),
            HumanMessage(
                content=f'I translated the sentence "{self._sentence_to_translate} to German as "{translation}". Tell me if there are any mistakes in translation, and give recommendation how it would be better to translate'
            ),
        ]
        answer = await chat.ainvoke(messages)
        return answer.content

    async def verify_answer(self, answer):
        three_form_schema = [
            ResponseSchema(name="infinitive", description="The infinitive form of the verb"),
            ResponseSchema(name="past", description="The past form of the verb"),
            ResponseSchema(name="participle", description="The past participle form of the verb, might be with the word `hat` or `ist`")
        ]
        output_parser = StructuredOutputParser.from_response_schemas(three_form_schema)
        format_instructions = output_parser.get_format_instructions()
        prompt = PromptTemplate(
            template='Parse the input into json. Input can be incorrect, nevertheless try to categorize the answer into three category, and paste them as is without any changes in the forms\n{format_instructions}\n{user_input}',
            input_variables=['user_input'],
            partial_variables={'format_instructions': format_instructions}
        )
        model_input = prompt.format_prompt(user_input=answer)
        model_output = await chat.ainvoke(model_input.to_messages())
        parsed_output = output_parser.parse(model_output.content)
        d = {
            'infinitive': self._infinitive,
            'past': self._past,
            'participle': self._participle
        }
        result = {}

        class AnswerValidater(BaseModel):
            answer_is_correct: bool = Field(description="The answer is correct")
            explanation: str = Field(description="Explanation where is a mistake.")

        try:
            for f in ('infinitive', 'past', 'participle'):
                user_answer = parsed_output[f]
                right_answer = d[f]
                if user_answer.strip().lower() == right_answer.strip().lower():
                    result[f] = '✅ ' + user_answer
                else:

                    parser = PydanticOutputParser(pydantic_object=AnswerValidater)
                    format_instructions = parser.get_format_instructions()
                    prompt = PromptTemplate(
                        template='Correct answer is "{correct}", user answered "{user}". Check the user\'s answer. Do not consider an answer with small spelling mistakes as a wrong answer. If there is a mistake try to explain why mistake were made, maybe there is similar word with different meaning, or the user confused german and english words. {format_instructions}',
                        input_variables=['correct', 'user'],
                        partial_variables={'format_instructions': format_instructions}

                    )
                    prompt_and_model = prompt | chat
                    model_output = await prompt_and_model.ainvoke({'correct': right_answer, 'user': user_answer})
                    parsed_model_output = await parser.ainvoke(model_output.content)
                    if parsed_model_output.answer_is_correct:
                        result[f] = '⚠️'  + mstrikethrough(user_answer) + ' -> ' + mbold(right_answer) + '\n     ' + parsed_model_output.explanation
                    else:
                        result[f] = '❗️'  + mstrikethrough(user_answer) + ' -> ' + mbold(right_answer) + '\n     ' + parsed_model_output.explanation
        except Exception as e:
            logging.exception(e)
            return 'An error happend while verifying results'

        return format_text('\n'.join([result['infinitive'], result['past'], result['participle']]))




class StrongVerbsExerciseManager:
    def __init__(self, csv_file):
        self._verbs = pd.read_csv(csv_file)

    async def create_exercise(self) -> StrongVerbsExercise:
        example = self._verbs.sample(1)
        return StrongVerbsExercise(example)


manager = StrongVerbsExerciseManager('../data/strong_verbs.csv')

def register_handlers(bot: AsyncTeleBot):

    @bot.message_handler(commands=['strong_verbs'], chat_types='private')
    async def new_exercise(message):
        exercise: StrongVerbsExercise = await manager.create_exercise()
        user_id = message.from_user.id
        chat_id = message.chat.id

        await bot.set_state(user_id, ExerciseStates.three_forms, chat_id)
        async with bot.retrieve_data(user_id, chat_id) as data:
            data['strong_verbs_exercise'] = exercise

        await bot.send_message(chat_id, await exercise.description())

    @bot.message_handler(commands=['keine_ahnung'], state=ExerciseStates.three_forms, chat_types='private')
    async def help(message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        async with bot.retrieve_data(user_id, chat_id) as data:
            exercise: StrongVerbsExercise = data['strong_verbs_exercise']

        await bot.send_message(chat_id, await exercise.help_with_forms())
        await bot.set_state(user_id, ExerciseStates.translation, chat_id)
        await bot.send_message(user_id, await exercise.translation_task())


    @bot.message_handler(state=ExerciseStates.three_forms, chat_types='private')
    async def verify_answer(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        async with bot.retrieve_data(user_id, chat_id) as data:
            exercise: StrongVerbsExercise = data['strong_verbs_exercise']

        check = await exercise.verify_answer(message.text)
        await bot.send_message(chat_id, check)

        await bot.set_state(user_id, ExerciseStates.translation, chat_id)
        await bot.send_message(user_id, await exercise.translation_task())

    @bot.message_handler(state=ExerciseStates.translation, chat_types='private')
    async def verify_translation(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        async with bot.retrieve_data(user_id, chat_id) as data:
            exercise: StrongVerbsExercise = data['strong_verbs_exercise']

        evaluation = await exercise.verify_translation(message.text)
        await bot.send_message(chat_id, evaluation)
