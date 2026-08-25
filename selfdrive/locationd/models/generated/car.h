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
void car_err_fun(double *nom_x, double *delta_x, double *out_6066785079692700737);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_386653618683565600);
void car_H_mod_fun(double *state, double *out_2911819638975789429);
void car_f_fun(double *state, double dt, double *out_7908585330617552733);
void car_F_fun(double *state, double dt, double *out_3633424257345620011);
void car_h_25(double *state, double *unused, double *out_8566594812092318047);
void car_H_25(double *state, double *unused, double *out_3585203320914240522);
void car_h_24(double *state, double *unused, double *out_7709351917136459488);
void car_H_24(double *state, double *unused, double *out_4055660802957579246);
void car_h_30(double *state, double *unused, double *out_3060647100788456434);
void car_H_30(double *state, double *unused, double *out_3714542268057480592);
void car_h_26(double *state, double *unused, double *out_2806316718466979703);
void car_H_26(double *state, double *unused, double *out_7326706639788296746);
void car_h_27(double *state, double *unused, double *out_8520521730607863741);
void car_H_27(double *state, double *unused, double *out_5889305579857905503);
void car_h_29(double *state, double *unused, double *out_617195554075987441);
void car_H_29(double *state, double *unused, double *out_7602668306727456536);
void car_h_28(double *state, double *unused, double *out_8625997807319031960);
void car_H_28(double *state, double *unused, double *out_5761676749912564506);
void car_h_31(double *state, double *unused, double *out_7164630353941861079);
void car_H_31(double *state, double *unused, double *out_3554557359037280094);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}