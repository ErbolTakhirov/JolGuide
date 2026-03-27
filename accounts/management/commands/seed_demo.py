from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

from accounts.models import GuideProfile, TouristProfile
from reviews.models import Review
from chats.models import ChatMessage
from bookings.models import BookingRequest
from matching.models import MatchRequest, MatchResult
from guides.models import GuideVerificationRequest
from experiences.models import Experience, ExperienceBooking, ExperienceReview

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with demo data (idempotent)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing old demo data...')
        
        # Удаляем старых демо-пользователей
        User.objects.filter(email__endswith='@demo.com').delete()
        # Также очистим отзывы, чаты и букинг, чтобы не плодить мусор
        ExperienceReview.objects.all().delete()
        ExperienceBooking.objects.all().delete()
        Experience.objects.all().delete()
        Review.objects.all().delete()
        ChatMessage.objects.all().delete()
        BookingRequest.objects.all().delete()
        MatchRequest.objects.all().delete()
        GuideProfile.objects.all().delete()
        TouristProfile.objects.all().delete()

        self.stdout.write('Creating Tourists...')
        t1 = User.objects.create_user(
            email='tourist1@demo.com',
            username='tourist_anna',
            password='demo1234',
            role='tourist',
            first_name='Anna',
            last_name='Smith'
        )
        t2 = User.objects.create_user(
            email='tourist2@demo.com',
            username='tourist_mike',
            password='demo1234',
            role='tourist',
            first_name='Mike',
            last_name='Jones'
        )

        self.stdout.write('Creating Guide Account...')
        g_owner = User.objects.create_user(
            email='guide1@demo.com',
            username='guide_azamat',
            password='demo1234',
            role='guide',
            first_name='Azamat',
            last_name='Beishenaliev'
        )

        self.stdout.write('Creating 8 Guide Profiles...')
        guides_data = [
            {
                'user': g_owner,
                'name': 'Азамат Бейшеналиев',
                'city': 'Бишкек',
                'languages': 'ru, en',
                'bio': 'Коренной бишкекчанин, покажу лучшие кофейни и горы вокруг города.',
                'services_text': 'Пешие туры по городу - $20\nПоездка в Ала-Арчу - $50',
                'price_from': 20.00,
                'is_verified': True,
            },
            {
                'name': 'Елена Иванова',
                'city': 'Алматы',
                'languages': 'ru, en',
                'bio': 'Гид по горам Заилийского Алатау. Люблю хайкинг и природу.',
                'services_text': 'Поход на Медеу - $30\nКок-Жайляу - $40',
                'price_from': 30.00,
                'is_verified': True,
            },
            {
                'name': 'Farrukh',
                'city': 'Ташкент',
                'languages': 'ru, en, uz',
                'bio': 'Эксперт по кулинарии и истории. Вкусный Ташкент ждет.',
                'services_text': 'Гастро-тур - $40\nСтарый город - $25',
                'price_from': 25.00,
                'is_verified': True,
            },
            {
                'name': 'Салтанат',
                'city': 'Бишкек',
                'languages': 'ru, de',
                'bio': 'Архитектура модерна и советское наследие Бишкека.',
                'services_text': 'Исторический центр - $15',
                'price_from': 15.00,
                'is_verified': False,
            },
            {
                'name': 'Timur',
                'city': 'Алматы',
                'languages': 'ru, en',
                'bio': 'Экстремальные туры и фрирайд.',
                'services_text': 'Фрирайд тур - $100',
                'price_from': 100.00,
                'is_verified': False,
            },
            {
                'name': 'Gulnara',
                'city': 'Бишкек',
                'languages': 'ru, en, tr',
                'bio': 'Поездки на Иссык-Куль и погружение в кочевую культуру.',
                'services_text': 'Тур на Иссык-Куль (2 дня) - $150',
                'price_from': 150.00,
                'is_verified': False,
            },
            {
                'name': 'Alisher',
                'city': 'Ташкент',
                'languages': 'ru, en',
                'bio': 'Поездки в Самарканд и Бухару из Ташкента.',
                'services_text': 'Дневной тур - $80',
                'price_from': 80.00,
                'is_verified': False,
            },
            {
                'name': 'Дмитрий',
                'city': 'Алматы',
                'languages': 'ru',
                'bio': 'Вечерняя Алматы, бары и современное искусство.',
                'services_text': 'Бар кроул - $20\nАрт-галереи - $15',
                'price_from': 15.00,
                'is_verified': False,
            },
        ]

        guide_objects = []
        for i, data in enumerate(guides_data):
            if 'user' not in data:
                # Генерим фейковых юзеров для остальных 7 гидов
                fake_user = User.objects.create_user(
                    email=f'fakeguide{i}@demo.com',
                    username=f'fakeguide{i}',
                    password='demo',
                    role='guide'
                )
                data['user'] = fake_user
            
            profile, _ = GuideProfile.objects.update_or_create(
                user=data.pop('user'),
                defaults=data,
            )
            guide_objects.append(profile)

        azamat = guide_objects[0]
        elena = guide_objects[1]
        farrukh = guide_objects[2]

        self.stdout.write('Creating 3 Bookings...')
        
        # Add a verification request for Azamat
        GuideVerificationRequest.objects.create(
            guide=azamat,
            legal_name='Азамат Бейшеналиев',
            display_name='Азамат',
            phone='+996 555 000111',
            city='Бишкек',
            languages='ru, en',
            bio='Коренной бишкекчанин',
            service_types='Пешие туры',
            agreed_to_safety_rules=True,
            status=GuideVerificationRequest.Status.APPROVED_LIMITED,
            reviewed_by=g_owner,
            reviewed_at=timezone.now()
        )

        b1 = BookingRequest.objects.create(
            tourist=t1, guide=azamat, service_name='Пеший тур', 
            date=timezone.now().date() + timedelta(days=2),
            comment='Мы будем с детьми', status=BookingRequest.Status.ACCEPTED
        )
        b2 = BookingRequest.objects.create(
            tourist=t2, guide=azamat, service_name='Ала-Арча', 
            date=timezone.now().date() + timedelta(days=5),
            comment='Нужен трансфер', status=BookingRequest.Status.PENDING
        )
        b3 = BookingRequest.objects.create(
            tourist=t1, guide=elena, service_name='Поход на Медеу', 
            date=timezone.now().date() + timedelta(days=10),
            comment='', status=BookingRequest.Status.DECLINED
        )

        self.stdout.write('Creating 5 Reviews...')
        # Чтобы оставить отзыв, нужна заявка в ACCEPTED, но через ORM мы можем создать и так.
        # Для соблюдения логики у Анны (t1) уже есть accepted заявка b1 к Азамату.
        r1 = Review.objects.create(tourist=t1, guide=azamat, rating=5, text='Отличная экскурсия! Очень понравилось.')
        # Добавим еще заявок для честности:
        BookingRequest.objects.create(tourist=t2, guide=elena, service_name='-', date=timezone.now().date(), status='accepted')
        BookingRequest.objects.create(tourist=t1, guide=farrukh, service_name='-', date=timezone.now().date(), status='accepted')
        BookingRequest.objects.create(tourist=t2, guide=farrukh, service_name='-', date=timezone.now().date(), status='accepted')
        BookingRequest.objects.create(tourist=t2, guide=guide_objects[3], service_name='-', date=timezone.now().date(), status='accepted')

        r2 = Review.objects.create(tourist=t2, guide=elena, rating=4, text='Хорошо, но погода подвела.')
        r3 = Review.objects.create(tourist=t1, guide=farrukh, rating=5, text='Очень вкусный плов!')
        r4 = Review.objects.create(tourist=t2, guide=farrukh, rating=4, text='Было интересно.')
        r5 = Review.objects.create(tourist=t2, guide=guide_objects[3], rating=3, text='Нормально.')

        # Пересчитаем рейтинги
        for g in GuideProfile.objects.all():
            reviews = Review.objects.filter(guide=g)
            if reviews.exists():
                g.rating = round(reviews.aggregate(avg=__import__('django.db.models', fromlist=['Avg']).Avg('rating'))['avg'], 2)
                g.save(update_fields=['rating'])

        self.stdout.write('Creating 10 Chat Messages...')
        # t1 <-> azamat (5 шт)
        ChatMessage.objects.create(sender=t1, receiver=azamat.user, text='Здравствуйте! Вы свободны на завтра?')
        ChatMessage.objects.create(sender=azamat.user, receiver=t1, text='Добрый день! Да, свободен.')
        ChatMessage.objects.create(sender=t1, receiver=azamat.user, text='Отлично, сколько будет стоить тур для двоих?')
        ChatMessage.objects.create(sender=azamat.user, receiver=t1, text='20$ за человека.')
        ChatMessage.objects.create(sender=t1, receiver=azamat.user, text='Супер, я отправляю заявку.')

        # t2 <-> azamat (3 шт)
        ChatMessage.objects.create(sender=t2, receiver=azamat.user, text='Привет, возите ли вы в горы?')
        ChatMessage.objects.create(sender=azamat.user, receiver=t2, text='Привет! Да, в Ала-Арчу.')
        ChatMessage.objects.create(sender=t2, receiver=azamat.user, text='Отправил заявку на 5 число.')

        # t1 <-> elena (2 шт)
        ChatMessage.objects.create(sender=t1, receiver=elena.user, text='Здравствуйте, мы из Бишкека, планируем в Алматы.')
        ChatMessage.objects.create(sender=elena.user, receiver=t1, text='Буду рада вас видеть!')

        # ══════════════════════════════════════════════
        # Demo Experiences, Bookings & Reviews
        # ══════════════════════════════════════════════
        self.stdout.write('Creating experiences...')

        exp1 = Experience.objects.create(
            guide=azamat,
            title='Обзорная экскурсия по Бишкеку',
            description='Пешая прогулка по центру города: площадь Ала-Тоо, Дубовый парк, Ошский базар и скрытые дворики.',
            city='Бишкек',
            category='walking',
            duration_hours=3,
            price=25.00,
            mode='private',
            datetime=timezone.now() + timedelta(days=5),
            meeting_point='Площадь Ала-Тоо, у флага',
            max_participants=1,
            is_active=True,
        )
        exp2 = Experience.objects.create(
            guide=azamat,
            title='Горный тур в Ала-Арчу',
            description='Групповой поход по ущелью Ала-Арча: водопады, панорамные виды, шашлыки на поляне.',
            city='Бишкек',
            category='nature',
            duration_hours=7,
            price=40.00,
            mode='group',
            datetime=timezone.now() + timedelta(days=7),
            meeting_point='Южные ворота парка Ала-Арча',
            max_participants=10,
            is_active=True,
        )
        exp3 = Experience.objects.create(
            guide=elena,
            title='Гастро-тур по Алматы',
            description='Дегустация уйгурской, казахской и корейской кухни в лучших заведениях города.',
            city='Алматы',
            category='food',
            duration_hours=4,
            price=35.00,
            mode='group',
            datetime=timezone.now() + timedelta(days=3),
            meeting_point='Зелёный Базар, центральный вход',
            max_participants=8,
            is_active=True,
        )
        exp4 = Experience.objects.create(
            guide=elena,
            title='Медеу и Чимбулак — зимняя сказка',
            description='Приватный тур на горнолыжный курорт: каток, подъёмник, горячий шоколад.',
            city='Алматы',
            category='adventure',
            duration_hours=5,
            price=60.00,
            mode='private',
            datetime=timezone.now() + timedelta(days=10),
            meeting_point='Остановка «Медеу»',
            max_participants=1,
            is_active=True,
        )

        # Bookings (some completed for reviews)
        self.stdout.write('Creating experience bookings...')
        b1 = ExperienceBooking.objects.create(
            experience=exp2, tourist=t1, num_guests=2, status='completed',
        )
        b2 = ExperienceBooking.objects.create(
            experience=exp3, tourist=t2, num_guests=1, status='completed',
        )
        b3 = ExperienceBooking.objects.create(
            experience=exp2, tourist=t2, num_guests=3, status='confirmed',
        )
        b4 = ExperienceBooking.objects.create(
            experience=exp1, tourist=t1, num_guests=1, status='pending',
        )

        # Reviews
        self.stdout.write('Creating experience reviews...')
        ExperienceReview.objects.create(
            booking=b1, experience=exp2, guide=azamat, tourist=t1,
            rating=5, text='Потрясающий поход! Азамат — лучший гид. Виды просто космос, шашлыки были великолепны.',
        )
        ExperienceReview.objects.create(
            booking=b2, experience=exp3, guide=elena, tourist=t2,
            rating=4, text='Очень вкусно, но хотелось бы больше остановок. Елена отлично рассказывает историю блюд!',
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded the database with demo data!'))
