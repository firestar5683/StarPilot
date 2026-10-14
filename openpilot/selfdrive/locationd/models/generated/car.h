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
void car_err_fun(double *nom_x, double *delta_x, double *out_8385818388315926896);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3457977650484525251);
void car_H_mod_fun(double *state, double *out_1868311171103980123);
void car_f_fun(double *state, double dt, double *out_1499231844596104733);
void car_F_fun(double *state, double dt, double *out_7736119846340090296);
void car_h_25(double *state, double *unused, double *out_5130465691248679820);
void car_H_25(double *state, double *unused, double *out_993002426764977143);
void car_h_24(double *state, double *unused, double *out_3830047811733214319);
void car_H_24(double *state, double *unused, double *out_5739511753731486177);
void car_h_30(double *state, double *unused, double *out_4178561097777020614);
void car_H_30(double *state, double *unused, double *out_1525330531742271484);
void car_h_26(double *state, double *unused, double *out_4041436014126362414);
void car_H_26(double *state, double *unused, double *out_2311523542995823458);
void car_h_27(double *state, double *unused, double *out_128792423587834175);
void car_H_27(double *state, double *unused, double *out_3748924602926214701);
void car_h_29(double *state, double *unused, double *out_1579423816216717342);
void car_H_29(double *state, double *unused, double *out_2035561876056663668);
void car_h_28(double *state, double *unused, double *out_7563935858016534988);
void car_H_28(double *state, double *unused, double *out_3046837141012866906);
void car_h_31(double *state, double *unused, double *out_8001670333771886589);
void car_H_31(double *state, double *unused, double *out_1685315440762471982);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}