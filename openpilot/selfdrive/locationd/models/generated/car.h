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
void car_err_fun(double *nom_x, double *delta_x, double *out_2719694004078796480);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_856919065793812544);
void car_H_mod_fun(double *state, double *out_7350016175302370423);
void car_f_fun(double *state, double dt, double *out_6616197954711019157);
void car_F_fun(double *state, double dt, double *out_4925250846992883324);
void car_h_25(double *state, double *unused, double *out_5036418257355363199);
void car_H_25(double *state, double *unused, double *out_3827035525312878746);
void car_h_24(double *state, double *unused, double *out_1369846818760663587);
void car_H_24(double *state, double *unused, double *out_2748536281278639355);
void car_h_30(double *state, double *unused, double *out_5637836414968726753);
void car_H_30(double *state, double *unused, double *out_3089654816178738009);
void car_h_26(double *state, double *unused, double *out_4551109766612262426);
void car_H_26(double *state, double *unused, double *out_7568538844186934970);
void car_h_27(double *state, double *unused, double *out_34744989694517554);
void car_H_27(double *state, double *unused, double *out_914891504378313098);
void car_h_29(double *state, double *unused, double *out_6553082936781777609);
void car_H_29(double *state, double *unused, double *out_3599886160493130193);
void car_h_28(double *state, double *unused, double *out_4587441039761590760);
void car_H_28(double *state, double *unused, double *out_5880870239560768509);
void car_h_31(double *state, double *unused, double *out_2726846999465309242);
void car_H_31(double *state, double *unused, double *out_3796389563435918318);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}