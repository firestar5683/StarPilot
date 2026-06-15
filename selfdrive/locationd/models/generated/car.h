#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_488496692945809667);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4539209272711951056);
void car_H_mod_fun(double *state, double *out_8602256134349546689);
void car_f_fun(double *state, double dt, double *out_5404650696097251297);
void car_F_fun(double *state, double dt, double *out_3720686995353807718);
void car_h_25(double *state, double *unused, double *out_2947196115150604911);
void car_H_25(double *state, double *unused, double *out_5079207495704181541);
void car_h_24(double *state, double *unused, double *out_5743512623925098853);
void car_H_24(double *state, double *unused, double *out_8637133094506504677);
void car_h_30(double *state, double *unused, double *out_1496564722521721744);
void car_H_30(double *state, double *unused, double *out_6450846236513753320);
void car_h_26(double *state, double *unused, double *out_7752389444480768998);
void car_H_26(double *state, double *unused, double *out_8383733465464982142);
void car_h_27(double *state, double *unused, double *out_6576952114136391720);
void car_H_27(double *state, double *unused, double *out_8625609548314178231);
void car_h_29(double *state, double *unused, double *out_6498237990182567389);
void car_H_29(double *state, double *unused, double *out_5940614892199361136);
void car_h_28(double *state, double *unused, double *out_6868118691912314251);
void car_H_28(double *state, double *unused, double *out_3025372781456291778);
void car_h_31(double *state, double *unused, double *out_8728712732208595769);
void car_H_31(double *state, double *unused, double *out_6290861327493552822);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}