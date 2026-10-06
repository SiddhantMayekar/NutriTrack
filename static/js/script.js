const counters = document.querySelectorAll(".counter");

const speed = 50;

const animateCounters = () => {

    counters.forEach(counter => {

        const target = +counter.getAttribute("data-target");

        const update = () => {

            const current = +counter.innerText;

            const increment = Math.ceil(target / speed);

            if(current < target){

                counter.innerText = current + increment;

                setTimeout(update,30);

            }

            else{

                counter.innerText = target.toLocaleString()+"+";

            }

        };

        update();

    });

};

const observer = new IntersectionObserver(entries=>{

    entries.forEach(entry=>{

        if(entry.isIntersecting){

            animateCounters();

            observer.disconnect();

        }

    });

});

observer.observe(document.querySelector("#community"));