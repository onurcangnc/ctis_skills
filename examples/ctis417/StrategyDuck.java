// Strategy, a behavioural pattern.
// Intent: define a family of algorithms, encapsulate each one, and make them
// interchangeable at runtime.
// Principle applied: encapsulate what varies, and favour composition over
// inheritance. The two behaviours are the parts that vary between duck types,
// so they leave the hierarchy and become objects the duck holds.

interface FlyBehavior {
    void fly();
}

interface QuackBehavior {
    void quack();
}

class FlyWithWings implements FlyBehavior {
    public void fly() {
        System.out.println("flying");
    }
}

class FlyNoWay implements FlyBehavior {
    public void fly() {
        System.out.println("cannot fly");
    }
}

class Quack implements QuackBehavior {
    public void quack() {
        System.out.println("quack");
    }
}

class Squeak implements QuackBehavior {
    public void quack() {
        System.out.println("squeak");
    }
}

abstract class Duck {
    protected FlyBehavior flyBehavior;
    protected QuackBehavior quackBehavior;

    public abstract void display();

    public void performFly() {
        flyBehavior.fly();
    }

    public void performQuack() {
        quackBehavior.quack();
    }

    // The setter is what makes the behaviour interchangeable at runtime.
    // Without it this is composition but not yet Strategy.
    public void setFlyBehavior(FlyBehavior flyBehavior) {
        this.flyBehavior = flyBehavior;
    }
}

class MallardDuck extends Duck {
    public MallardDuck() {
        this.flyBehavior = new FlyWithWings();
        this.quackBehavior = new Quack();
    }

    public void display() {
        System.out.println("mallard");
    }
}

class RubberDuck extends Duck {
    public RubberDuck() {
        this.flyBehavior = new FlyNoWay();
        this.quackBehavior = new Squeak();
    }

    public void display() {
        System.out.println("rubber");
    }
}

public class StrategyDuck {
    public static void main(String[] args) {
        Duck mallard = new MallardDuck();
        Duck rubber = new RubberDuck();

        mallard.performFly();
        mallard.performQuack();
        rubber.performFly();
        rubber.performQuack();

        // A grounded mallard keeps its type and changes only its behaviour.
        mallard.setFlyBehavior(new FlyNoWay());
        mallard.performFly();

        System.out.println("STRATEGY_OK");
    }
}
